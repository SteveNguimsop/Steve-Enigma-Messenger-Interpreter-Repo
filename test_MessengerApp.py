import tempfile
import unittest
from pathlib import Path
from unittest import mock

import MessengerApp as messenger_module
from ConversationManager import ConversationManager
from GitRepositoryManager import GitError
from MessengerApp import MessengerApp


class FakeGit:
    def __init__(self, push_result=True):
        self.pulled = 0
        self.pushed = []
        self.push_result = push_result

    def pull(self):
        self.pulled += 1
        return True

    def commit_and_push(self, files, message="Update conversation"):
        self.pushed.append((list(files), message))
        return self.push_result


class AppTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.git = FakeGit()
        self.printed = []

    def tearDown(self):
        self._tmp.cleanup()

    def make_app(self, answers):
        answers = iter(answers)
        return MessengerApp(
            self.repo, git=self.git, conversations=ConversationManager(self.repo),
            input_func=lambda prompt: next(answers), output_func=self.printed.append)

    def read_back(self, a, b):
        return ConversationManager(self.repo).open_conversation(a, b)


class TestRun(AppTestCase):
    def test_new_conversation(self):
        self.make_app(["Steve", "Alice", "Hello Alice"]).run()
        self.assertEqual(self.git.pulled, 1)
        self.assertEqual(self.git.pushed, [(["Alice-Steve.txt"], "Update Alice-Steve.txt")])
        self.assertIn("Starting a new conversation: Alice-Steve.txt", "\n".join(self.printed))
        self.assertEqual(self.read_back("Alice", "Steve"), "[Steve]: Hello Alice\n")

    def test_existing_conversation_prints_history(self):
        self.make_app(["Steve", "Alice", "Hello Alice"]).run()
        self.printed.clear()
        self.make_app(["Alice", "Steve", "Hi Steve"]).run()
        output = "\n".join(self.printed)
        self.assertIn("[Steve]: Hello Alice", output)
        self.assertEqual(self.read_back("Steve", "Alice"), "[Steve]: Hello Alice\n[Alice]: Hi Steve\n")

    def test_file_on_disk_is_not_plaintext(self):
        self.make_app(["Steve", "Alice", "top secret plan"]).run()
        self.assertNotIn("secret", (self.repo / "Alice-Steve.txt").read_text())

    def test_commit_message_does_not_leak_text(self):
        self.make_app(["Steve", "Alice", "top secret plan"]).run()
        self.assertNotIn("secret", self.git.pushed[0][1])

    def test_nothing_pushed_message(self):
        self.git.push_result = False
        self.make_app(["Steve", "Alice", "hi"]).run()
        self.assertIn("Nothing changed, so nothing was pushed.", self.printed)


class TestPrompts(AppTestCase):
    def test_invalid_username_reprompts(self):
        app = self.make_app(["9lives", "bad name", "Steve"])
        self.assertEqual(app.prompt_username("? "), "Steve")
        self.assertEqual(len(self.printed), 2)

    def test_cannot_message_self(self):
        app = self.make_app(["steve", "Alice"])
        app.current_user = "Steve"
        self.assertEqual(app.select_recipient(), "Alice")
        self.assertIn("You cannot message yourself. Choose another user.", self.printed)

    def test_empty_message_reprompts(self):
        self.make_app(["Steve", "Alice", "   ", "", "finally"]).run()
        self.assertEqual(self.printed.count("Message cannot be empty."), 2)
        self.assertEqual(self.read_back("Alice", "Steve"), "[Steve]: finally\n")


class TestMain(unittest.TestCase):
    def test_missing_repo(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("builtins.print") as fake_print:
            self.assertEqual(messenger_module.main(["MessengerApp.py", tmp]), 1)
            self.assertIn("Clone it first", fake_print.call_args[0][0])

    def test_runs_app(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / ".git").mkdir()
            with mock.patch.object(MessengerApp, "run") as run:
                self.assertEqual(messenger_module.main(["MessengerApp.py", tmp]), 0)
                run.assert_called_once()

    def test_git_error_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("builtins.print") as fake_print:
            (Path(tmp) / ".git").mkdir()
            with mock.patch.object(MessengerApp, "run", side_effect=GitError("boom")):
                self.assertEqual(messenger_module.main(["MessengerApp.py", tmp]), 1)
            self.assertIn("boom", fake_print.call_args[0][0])

    def test_ctrl_c_exits_cleanly(self):
        with tempfile.TemporaryDirectory() as tmp, mock.patch("builtins.print"):
            (Path(tmp) / ".git").mkdir()
            with mock.patch.object(MessengerApp, "run", side_effect=KeyboardInterrupt):
                self.assertEqual(messenger_module.main(["MessengerApp.py", tmp]), 130)

    def test_default_repo_is_sibling_folder(self):
        self.assertEqual(messenger_module.DEFAULT_UEMR_PATH.name, "USAO-Enigma-Messenger-Repo")


if __name__ == "__main__":
    unittest.main()
