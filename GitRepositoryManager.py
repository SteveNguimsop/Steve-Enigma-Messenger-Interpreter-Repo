"""Pulls and pushes the USAO-Enigma-Messenger-Repo (UEMR) with git."""

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


class GitAccessError(GitError):
    """GitHub refused the request: no write access, or not signed in."""


ACCESS_MESSAGE = (
    "GitHub refused access to the message repo (you don't have write access).\n"
    "Ask the repo owner to add your GitHub account as a collaborator, and make sure git "
    "is signed in with that account.\n"
    "Your message is saved in your local copy and will be uploaded the next time you "
    "send a message after access is granted."
)

# Text git prints when GitHub rejects a push for permission or login reasons.
ACCESS_DENIED_MARKERS = (
    "permission to",            # remote: Permission to owner/repo.git denied to user.
    "returned error: 403",      # HTTPS 403 Forbidden
    "permission denied",        # SSH: Permission denied (publickey)
    "authentication failed",    # bad or missing credentials
    "write access to repository not granted",
)

NETWORK_COMMANDS = {"push", "pull", "fetch", "ls-remote"}


class GitRepositoryManager:
    DEFAULT_BRANCH = "main"

    def __init__(self, repo_path: str | Path, remote: str = "origin"):
        self.repo_path = Path(repo_path).resolve()
        self.remote = remote

    @staticmethod
    def is_access_denied(stderr: str) -> bool:
        text = stderr.lower()
        return any(marker in text for marker in ACCESS_DENIED_MARKERS)

    def run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            if args and args[0] in NETWORK_COMMANDS and self.is_access_denied(result.stderr):
                raise GitAccessError(ACCESS_MESSAGE)
            raise GitError(f"git {' '.join(args)} failed:\n{result.stderr.strip()}")
        return result

    def remote_branch(self) -> str | None:
        """Name of the remote's default branch, or None if the remote is empty."""
        heads = self.run_git("ls-remote", "--symref", self.remote, "HEAD").stdout
        for line in heads.splitlines():
            if line.startswith("ref: refs/heads/"):
                return line.split("\t")[0].removeprefix("ref: refs/heads/")
        branches = self.run_git("ls-remote", "--heads", self.remote).stdout.split()
        if not branches:
            return None
        names = [ref.removeprefix("refs/heads/") for ref in branches[1::2]]
        return self.DEFAULT_BRANCH if self.DEFAULT_BRANCH in names else names[0]

    def pull(self) -> bool:
        """Bring the local UEMR up to date. Returns False if the remote is empty."""
        branch = self.remote_branch()
        if branch is None:
            return False
        result = self.run_git("pull", "--rebase", self.remote, branch, check=False)
        if result.returncode != 0:
            if self.is_access_denied(result.stderr):
                raise GitAccessError(ACCESS_MESSAGE)
            # An earlier unsent message clashes with newer messages on GitHub.
            # Drop the unsent commit so the clone matches GitHub and stays usable.
            self.run_git("rebase", "--abort", check=False)
            self.run_git("reset", "--hard", f"{self.remote}/{branch}", check=False)
            raise GitError(
                "An earlier message that was never uploaded clashed with newer messages "
                "on GitHub, so it was discarded. Please run the messenger again."
            )
        return True

    def commit_and_push(self, files: list[str], message: str = "Update conversation") -> bool:
        """Commit the given files and push them. Returns False if nothing changed."""
        self.run_git("add", "--", *files)
        if self.run_git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        self.run_git("commit", "-m", message)

        branch = self.remote_branch() or self.current_branch()
        push = self.run_git("push", self.remote, f"HEAD:{branch}", check=False)
        if push.returncode != 0:
            if self.is_access_denied(push.stderr):
                # Keep the local commit so it goes up once access is granted.
                raise GitAccessError(ACCESS_MESSAGE)
            # Someone else pushed first: replay our commit on top of theirs and retry.
            rebase = self.run_git("pull", "--rebase", self.remote, branch, check=False)
            if rebase.returncode != 0:
                # Both people changed the same encrypted file. Drop our local commit
                # so the clone matches GitHub again; the user just resends.
                self.run_git("rebase", "--abort", check=False)
                self.run_git("reset", "--hard", f"{self.remote}/{branch}", check=False)
                raise GitError(
                    "Someone else wrote to this conversation at the same time, so your "
                    "message was not sent. Please run the messenger again and resend it."
                )
            self.run_git("push", self.remote, f"HEAD:{branch}")
        self.run_git("branch", f"--set-upstream-to={self.remote}/{branch}", check=False)
        return True

    def current_branch(self) -> str:
        name = self.run_git("symbolic-ref", "--short", "HEAD", check=False).stdout.strip()
        return name or self.DEFAULT_BRANCH
