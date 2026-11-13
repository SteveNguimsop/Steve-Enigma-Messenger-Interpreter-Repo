import random
import tempfile
import unittest
from pathlib import Path

from ConversationManager import ConversationManager
from RotatingCaesarCipher import RotatingCaesarCipher


class ConversationTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        self.cipher = RotatingCaesarCipher(random.Random(42))
        self.manager = ConversationManager(self.repo, cipher=self.cipher)

    def tearDown(self):
        self._tmp.cleanup()

    def write_encrypted(self, filename, text, shift):
        (self.repo / filename).write_bytes(self.cipher.encrypt(text, shift).encode("utf-8"))


class TestExists(ConversationTestCase):
    def test_missing_file(self):
        self.assertFalse(self.manager.exists("Alice-Bob.txt"))

    def test_existing_file(self):
        (self.repo / "Alice-Bob.txt").write_text("")
        self.assertTrue(self.manager.exists("Alice-Bob.txt"))

    def test_rejects_paths_outside_repo(self):
        with self.assertRaises(ValueError):
            self.manager.exists("../Alice-Bob.txt")


class TestOpenConversation(ConversationTestCase):
    def test_new_conversation_creates_empty_file(self):
        text = self.manager.open_conversation("Bob", "Alice")
        self.assertEqual(text, "")
        self.assertEqual(self.manager.current_filename, "Alice-Bob.txt")
        self.assertEqual((self.repo / "Alice-Bob.txt").read_text(), "")
        self.assertIsNone(self.manager.last_shift)

    def test_existing_conversation_is_decrypted(self):
        plain = "[Alice]: Did you get my message?\n[Bob]: Yes I did\n"
        self.write_encrypted("Alice-Bob.txt", plain, 11)
        self.assertEqual(self.manager.open_conversation("Alice", "Bob"), plain)
        self.assertEqual(self.manager.last_shift, 11)

    def test_windows_line_endings_are_normalized(self):
        plain = "[Alice]: hi\n[Bob]: hello\n"
        encrypted = self.cipher.encrypt(plain, 4).replace("\n", "\r\n")
        (self.repo / "Alice-Bob.txt").write_bytes(encrypted.encode("utf-8"))
        self.assertEqual(self.manager.open_conversation("Alice", "Bob"), plain)

    def test_invalid_users_raise(self):
        with self.assertRaises(ValueError):
            self.manager.open_conversation("Alice", "B-o-b")
        self.assertEqual(list(self.repo.iterdir()), [])

    def test_creates_repo_folder_if_missing(self):
        manager = ConversationManager(self.repo / "sub", cipher=self.cipher)
        manager.open_conversation("Alice", "Bob")
        self.assertTrue((self.repo / "sub" / "Alice-Bob.txt").is_file())


class TestAppendMessage(ConversationTestCase):
    def test_first_message(self):
        self.manager.open_conversation("Alice", "Bob")
        self.assertEqual(self.manager.append_message("Alice", "Hello Bob"), "[Alice]: Hello Bob\n")

    def test_appends_to_end(self):
        self.write_encrypted("Alice-Bob.txt", "[Alice]: Hello Bob\n", 3)
        self.manager.open_conversation("Alice", "Bob")
        self.assertEqual(self.manager.append_message("Bob", "Hi Alice"),
                         "[Alice]: Hello Bob\n[Bob]: Hi Alice\n")

    def test_adds_missing_newline(self):
        self.manager.current_text = "[Alice]: no newline"
        self.assertEqual(self.manager.append_message("Bob", "ok"),
                         "[Alice]: no newline\n[Bob]: ok\n")

    def test_message_collapsed_to_one_line(self):
        self.assertEqual(self.manager.append_message("Bob", "  two\nlines  "), "[Bob]: two lines\n")

    def test_empty_message_raises(self):
        with self.assertRaises(ValueError):
            self.manager.append_message("Bob", "   ")

    def test_invalid_user_raises(self):
        with self.assertRaises(ValueError):
            self.manager.append_message("B ob", "hi")


class TestSaveConversation(ConversationTestCase):
    def test_file_is_encrypted_not_plaintext(self):
        self.manager.open_conversation("Alice", "Bob")
        text = self.manager.append_message("Alice", "secret meeting at noon")
        shift = self.manager.save_conversation("Alice-Bob.txt", text)
        on_disk = (self.repo / "Alice-Bob.txt").read_bytes().decode("utf-8")
        self.assertNotIn("secret", on_disk)
        self.assertEqual(self.cipher.decrypt(on_disk, shift), text)

    def test_uses_lf_line_endings(self):
        self.manager.open_conversation("Alice", "Bob")
        self.manager.save_conversation("Alice-Bob.txt", "[Alice]: a\n[Bob]: b\n")
        self.assertNotIn(b"\r", (self.repo / "Alice-Bob.txt").read_bytes())

    def test_new_shift_differs_from_previous(self):
        for previous in range(1, 26):
            with self.subTest(previous=previous):
                self.write_encrypted("Alice-Bob.txt", "[Alice]: Hello there Bob\n", previous)
                self.manager.open_conversation("Alice", "Bob")
                text = self.manager.append_message("Bob", "hey")
                self.assertNotEqual(self.manager.save_conversation("Alice-Bob.txt", text), previous)

    def test_full_round_trip_between_two_users(self):
        alice = ConversationManager(self.repo)
        alice.open_conversation("Alice", "Bob")
        alice.save_conversation(alice.current_filename, alice.append_message("Alice", "Hi Bob"))

        bob = ConversationManager(self.repo)
        self.assertEqual(bob.open_conversation("Bob", "Alice"), "[Alice]: Hi Bob\n")
        bob.save_conversation(bob.current_filename, bob.append_message("Bob", "Hi Alice"))

        again = ConversationManager(self.repo)
        self.assertEqual(again.open_conversation("Alice", "Bob"),
                         "[Alice]: Hi Bob\n[Bob]: Hi Alice\n")


if __name__ == "__main__":
    unittest.main()
