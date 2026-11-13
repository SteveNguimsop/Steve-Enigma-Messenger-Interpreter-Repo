"""Pulls and pushes the USAO-Enigma-Messenger-Repo (UEMR) with git."""

import subprocess
from pathlib import Path


class GitError(RuntimeError):
    pass


class GitRepositoryManager:
    DEFAULT_BRANCH = "main"

    def __init__(self, repo_path: str | Path, remote: str = "origin"):
        self.repo_path = Path(repo_path).resolve()
        self.remote = remote

    def run_git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        result = subprocess.run(
            ["git", *args],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
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
        self.run_git("pull", "--rebase", self.remote, branch)
        return True

    def commit_and_push(self, files: list[str], message: str = "Update conversation") -> bool:
        """Commit the given files and push them. Returns False if nothing changed."""
        self.run_git("add", "--", *files)
        if self.run_git("diff", "--cached", "--quiet", check=False).returncode == 0:
            return False
        self.run_git("commit", "-m", message)

        branch = self.remote_branch() or self.current_branch()
        if self.run_git("push", self.remote, f"HEAD:{branch}", check=False).returncode != 0:
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
