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

from GitRepositoryManager import GitError, GitRepositoryManager

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
