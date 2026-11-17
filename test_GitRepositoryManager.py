"""Tests GitRepositoryManager against real git repositories in a temp folder.

A local bare repository stands in for GitHub, so these tests never use the
network and never touch the real USAO-Enigma-Messenger-Repo.
"""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from GitRepositoryManager import GitAccessError, GitError, GitRepositoryManager

GIT_ENV = {
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


@unittest.skipIf(shutil.which("git") is None, "git is not installed")
class GitTestCase(unittest.TestCase):
    def setUp(self):
        self._env = {key: os.environ.get(key) for key in GIT_ENV}
        os.environ.update(GIT_ENV)
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.remote = self.root / "github.git"
        git(self.root, "init", "--bare", "--initial-branch=main", str(self.remote))

    def tearDown(self):
        for key, value in self._env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self._tmp.cleanup()

    def clone(self, name):
        git(self.root, "clone", str(self.remote), name)
        return self.root / name

    def write(self, repo, filename, content):
        (repo / filename).write_text(content, encoding="utf-8")

    def remote_file(self, filename):
        return git(self.remote, "show", f"main:{filename}").stdout


class TestPull(GitTestCase):
    def test_pull_empty_remote_returns_false(self):
        alice = self.clone("alice")
        self.assertFalse(GitRepositoryManager(alice).pull())

    def test_pull_gets_new_files(self):
        alice, bob = self.clone("alice"), self.clone("bob")
        self.write(alice, "Alice-Bob.txt", "one")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])

        self.assertTrue(GitRepositoryManager(bob).pull())
        self.assertEqual((bob / "Alice-Bob.txt").read_text(), "one")

    def test_pull_on_existing_history(self):
        alice, bob = self.clone("alice"), self.clone("bob")
        self.write(alice, "Alice-Bob.txt", "one")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])
        GitRepositoryManager(bob).pull()
        self.write(alice, "Alice-Bob.txt", "two")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])

        GitRepositoryManager(bob).pull()
        self.assertEqual((bob / "Alice-Bob.txt").read_text(), "two")


class TestCommitAndPush(GitTestCase):
    def test_first_push_creates_main_branch(self):
        alice = self.clone("alice")
        self.write(alice, "Alice-Bob.txt", "hello")
        self.assertTrue(GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"], "Update Alice-Bob.txt"))
        self.assertEqual(self.remote_file("Alice-Bob.txt"), "hello")
        log = git(self.remote, "log", "-1", "--format=%s", "main").stdout.strip()
        self.assertEqual(log, "Update Alice-Bob.txt")

    def test_nothing_to_commit_returns_false(self):
        alice = self.clone("alice")
        self.write(alice, "Alice-Bob.txt", "hello")
        manager = GitRepositoryManager(alice)
        manager.commit_and_push(["Alice-Bob.txt"])
        self.assertFalse(manager.commit_and_push(["Alice-Bob.txt"]))

    def test_only_listed_files_are_committed(self):
        alice = self.clone("alice")
        self.write(alice, "Alice-Bob.txt", "hello")
        self.write(alice, "stray.txt", "do not publish")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])
        files = git(self.remote, "ls-tree", "--name-only", "main").stdout.split()
        self.assertEqual(files, ["Alice-Bob.txt"])

    def test_retries_when_someone_else_pushed_a_different_file(self):
        alice, bob = self.clone("alice"), self.clone("bob")
        self.write(alice, "Alice-Bob.txt", "from alice")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])

        # Bob has not pulled, so his first push is rejected and must be rebased.
        self.write(bob, "Bob-Carl.txt", "from bob")
        self.assertTrue(GitRepositoryManager(bob).commit_and_push(["Bob-Carl.txt"]))
        self.assertEqual(self.remote_file("Alice-Bob.txt"), "from alice")
        self.assertEqual(self.remote_file("Bob-Carl.txt"), "from bob")

    def test_conflict_on_same_file_raises_and_resets(self):
        alice, bob = self.clone("alice"), self.clone("bob")
        self.write(alice, "Alice-Bob.txt", "base")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])
        GitRepositoryManager(bob).pull()

        self.write(alice, "Alice-Bob.txt", "alice wins")
        GitRepositoryManager(alice).commit_and_push(["Alice-Bob.txt"])
        self.write(bob, "Alice-Bob.txt", "bob loses")
        with self.assertRaises(GitError):
            GitRepositoryManager(bob).commit_and_push(["Alice-Bob.txt"])

        # Bob's clone is usable again and matches GitHub.
        self.assertEqual((bob / "Alice-Bob.txt").read_text(), "alice wins")
        self.assertTrue(GitRepositoryManager(bob).pull())
        self.assertEqual(self.remote_file("Alice-Bob.txt"), "alice wins")


class TestErrors(GitTestCase):
    def test_not_a_repository_raises(self):
        folder = self.root / "plain"
        folder.mkdir()
        with self.assertRaises(GitError):
            GitRepositoryManager(folder, remote="nowhere").pull()

    def test_remote_branch_none_when_empty(self):
        self.assertIsNone(GitRepositoryManager(self.clone("alice")).remote_branch())


GITHUB_403 = (
    "remote: Permission to qtranokc/USAO-Enigma-Messenger-Repo.git denied to JDiegoF19.\n"
    "fatal: unable to access 'https://github.com/qtranokc/USAO-Enigma-Messenger-Repo.git/': "
    "The requested URL returned error: 403\n"
)


class TestIsAccessDenied(unittest.TestCase):
    def test_recognizes_github_and_ssh_errors(self):
        for stderr in [GITHUB_403,
                       "git@github.com: Permission denied (publickey).",
                       "fatal: Authentication failed for 'https://github.com/x/y.git/'",
                       "remote: Write access to repository not granted."]:
            with self.subTest(stderr=stderr):
                self.assertTrue(GitRepositoryManager.is_access_denied(stderr))

    def test_ignores_other_errors(self):
        for stderr in ["! [rejected] HEAD -> main (fetch first)",
                       "fatal: unable to access: Could not resolve host: github.com", ""]:
            with self.subTest(stderr=stderr):
                self.assertFalse(GitRepositoryManager.is_access_denied(stderr))


class TestAccessErrorsMocked(unittest.TestCase):
    def failing_git(self, stderr):
        return mock.patch("GitRepositoryManager.subprocess.run",
                          return_value=subprocess.CompletedProcess([], 128, "", stderr))

    def test_pull_403_raises_access_error(self):
        manager = GitRepositoryManager(".")
        with mock.patch.object(manager, "remote_branch", return_value="main"), \
                self.failing_git(GITHUB_403):
            with self.assertRaises(GitAccessError) as caught:
                manager.pull()
        self.assertIn("collaborator", str(caught.exception))

    def test_ls_remote_403_raises_access_error(self):
        with self.failing_git(GITHUB_403):
            with self.assertRaises(GitAccessError):
                GitRepositoryManager(".").remote_branch()

    def test_local_permission_problem_is_not_an_access_error(self):
        with self.failing_git("error: unable to unlink: Permission denied"):
            with self.assertRaises(GitError) as caught:
                GitRepositoryManager(".").run_git("add", "x.txt")
        self.assertNotIsInstance(caught.exception, GitAccessError)


class TestAccessDenied(GitTestCase):
    """The fake GitHub rejects pushes the way GitHub does for non-collaborators."""

    def deny_pushes(self):
        hook = self.remote / "hooks" / "pre-receive"
        hook.write_text("#!/bin/sh\n"
                        "echo 'Permission to qtranokc/USAO-Enigma-Messenger-Repo.git "
                        "denied to JDiegoF19.' >&2\nexit 1\n", newline="\n")
        hook.chmod(0o755)

    def allow_pushes(self):
        (self.remote / "hooks" / "pre-receive").unlink()

    def commit_count(self, repo, ref="HEAD"):
        return int(git(repo, "rev-list", "--count", ref).stdout)

    def test_denied_push_raises_and_keeps_local_commit(self):
        juan = self.clone("juan")
        self.deny_pushes()
        self.write(juan, "JDiegoF19-Steve.txt", "hello")
        with self.assertRaises(GitAccessError) as caught:
            GitRepositoryManager(juan).commit_and_push(["JDiegoF19-Steve.txt"])
        self.assertIn("write access", str(caught.exception))
        self.assertEqual(self.commit_count(juan), 1)
        self.assertEqual(git(self.remote, "ls-remote", "--heads", ".").stdout, "")

    def test_unsent_message_is_uploaded_after_access_granted(self):
        juan = self.clone("juan")
        self.deny_pushes()
        self.write(juan, "JDiegoF19-Steve.txt", "first")
        with self.assertRaises(GitAccessError):
            GitRepositoryManager(juan).commit_and_push(["JDiegoF19-Steve.txt"])

        self.allow_pushes()
        manager = GitRepositoryManager(juan)
        manager.pull()
        self.write(juan, "JDiegoF19-Steve.txt", "first + second")
        self.assertTrue(manager.commit_and_push(["JDiegoF19-Steve.txt"]))
        self.assertEqual(self.commit_count(self.remote, "main"), 2)
        self.assertEqual(self.remote_file("JDiegoF19-Steve.txt"), "first + second")

    def test_pull_recovers_when_unsent_message_conflicts(self):
        steve, juan = self.clone("steve"), self.clone("juan")
        self.write(steve, "JDiegoF19-Steve.txt", "base")
        GitRepositoryManager(steve).commit_and_push(["JDiegoF19-Steve.txt"])
        GitRepositoryManager(juan).pull()

        self.deny_pushes()
        self.write(juan, "JDiegoF19-Steve.txt", "juan unsent")
        with self.assertRaises(GitAccessError):
            GitRepositoryManager(juan).commit_and_push(["JDiegoF19-Steve.txt"])

        self.allow_pushes()
        self.write(steve, "JDiegoF19-Steve.txt", "steve newer")
        GitRepositoryManager(steve).commit_and_push(["JDiegoF19-Steve.txt"])

        with self.assertRaises(GitError) as caught:
            GitRepositoryManager(juan).pull()
        self.assertNotIsInstance(caught.exception, GitAccessError)
        # Juan's clone matches GitHub, is not stuck mid-rebase, and pulls cleanly again.
        self.assertEqual((juan / "JDiegoF19-Steve.txt").read_text(), "steve newer")
        self.assertEqual(git(juan, "status", "--porcelain").stdout, "")
        self.assertTrue(GitRepositoryManager(juan).pull())


class TestRemoteBranchFallback(unittest.TestCase):
    """Some servers do not report which branch HEAD points to."""

    def branch_for(self, heads_output):
        manager = GitRepositoryManager(".")

        def fake_git(*args, check=True):
            stdout = "" if "--symref" in args else heads_output
            return subprocess.CompletedProcess(args, 0, stdout, "")

        with mock.patch.object(manager, "run_git", side_effect=fake_git):
            return manager.remote_branch()

    def test_prefers_main(self):
        self.assertEqual(self.branch_for("abc\trefs/heads/dev\ndef\trefs/heads/main\n"), "main")

    def test_uses_only_branch(self):
        self.assertEqual(self.branch_for("abc\trefs/heads/master\n"), "master")


if __name__ == "__main__":
    unittest.main()
