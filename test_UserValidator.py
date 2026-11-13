import unittest

from UserValidator import UserValidator


class TestIsValid(unittest.TestCase):
    def setUp(self):
        self.validator = UserValidator()

    def test_valid_names(self):
        for name in ["Steve", "a", "Bob2", "X9y8", "alice"]:
            with self.subTest(name=name):
                self.assertTrue(self.validator.is_valid(name))

    def test_invalid_names(self):
        for name in ["", "2Bob", "Bob-Smith", "Bob Smith", "bob_1", "bob!", "../etc",
                     "Bob\n", "José", None, 42]:
            with self.subTest(name=name):
                self.assertFalse(self.validator.is_valid(name))


class TestConversationFilename(unittest.TestCase):
    def setUp(self):
        self.validator = UserValidator()

    def test_alphabetical_order(self):
        self.assertEqual(self.validator.conversation_filename("Alice", "Bob"), "Alice-Bob.txt")

    def test_order_of_arguments_does_not_matter(self):
        self.assertEqual(self.validator.conversation_filename("Bob", "Alice"), "Alice-Bob.txt")

    def test_case_insensitive_ordering(self):
        self.assertEqual(self.validator.conversation_filename("bob", "Alice"), "Alice-bob.txt")

    def test_digits_in_names(self):
        self.assertEqual(self.validator.conversation_filename("user2", "user10"), "user10-user2.txt")

    def test_invalid_user_raises(self):
        with self.assertRaises(ValueError):
            self.validator.conversation_filename("Alice", "9Bob")

    def test_same_user_raises(self):
        with self.assertRaises(ValueError):
            self.validator.conversation_filename("Steve", "steve")


class TestUsersFromFilename(unittest.TestCase):
    def setUp(self):
        self.validator = UserValidator()

    def test_round_trip(self):
        filename = self.validator.conversation_filename("Zed", "Amy")
        self.assertEqual(self.validator.users_from_filename(filename), ("Amy", "Zed"))

    def test_rejects_bad_filenames(self):
        for name in ["Alice-Bob", "Alice.txt", "../Alice-Bob.txt", "Alice-Bob.txt.bak",
                     "README.md", "1A-Bob.txt"]:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    self.validator.users_from_filename(name)


if __name__ == "__main__":
    unittest.main()
