import random
import unittest

from RotatingCaesarCipher import RotatingCaesarCipher


class TestEncrypt(unittest.TestCase):
    """Expected values from Individual Project 2 (TDD-Project-Repo)."""

    def setUp(self):
        self.cipher = RotatingCaesarCipher()

    def test_shift_zero_is_identity(self):
        self.assertEqual(self.cipher.encrypt("HELLO", 0), "HELLO")

    def test_uppercase(self):
        self.assertEqual(self.cipher.encrypt("HELLO", 2), "JIRTY")

    def test_mixed_case_assignment_example(self):
        self.assertEqual(self.cipher.encrypt("Hello", 2), "Jirty")

    def test_shift_three(self):
        self.assertEqual(self.cipher.encrypt("Hello", 3), "Kkuxd")

    def test_non_letters_unchanged_and_do_not_rotate(self):
        self.assertEqual(self.cipher.encrypt("Hello World!", 3), "Kkuxd Ojpmh!")

    def test_increasing_shift(self):
        self.assertEqual(self.cipher.encrypt("ABC", 1), "BDF")

    def test_lowercase_with_punctuation(self):
        self.assertEqual(self.cipher.encrypt("abc!", 2), "cfi!")

    def test_wraps_around_alphabet(self):
        self.assertEqual(self.cipher.encrypt("Zz 123", 1), "Ab 123")

    def test_newlines_preserved(self):
        encrypted = self.cipher.encrypt("[A]: hi\n[B]: yo\n", 5)
        self.assertEqual(encrypted.count("\n"), 2)
        self.assertTrue(encrypted.endswith("\n"))

    def test_empty_string(self):
        self.assertEqual(self.cipher.encrypt("", 7), "")

    def test_non_ascii_letters_unchanged(self):
        self.assertEqual(self.cipher.encrypt("é", 4), "é")

    def test_shift_equivalent_mod_26(self):
        self.assertEqual(self.cipher.encrypt("Hello", 29), self.cipher.encrypt("Hello", 3))

    def test_original_method_names(self):
        self.assertEqual(self.cipher.RCC_encrypt("Hello", 2), "Jirty")
        self.assertEqual(self.cipher.RCC_decrypt("Jirty", 2), "Hello")


class TestDecrypt(unittest.TestCase):
    def setUp(self):
        self.cipher = RotatingCaesarCipher()

    def test_assignment_example(self):
        self.assertEqual(self.cipher.decrypt("Jirty", 2), "Hello")

    def test_shift_three(self):
        self.assertEqual(self.cipher.decrypt("Kkuxd", 3), "Hello")

    def test_with_punctuation(self):
        self.assertEqual(self.cipher.decrypt("Kkuxd Ojpmh!", 3), "Hello World!")

    def test_wraps_around_alphabet(self):
        self.assertEqual(self.cipher.decrypt("Ab 123", 1), "Zz 123")

    def test_round_trip_every_shift(self):
        text = "[Alice]: Hi Bob, are we meeting at 3pm?\n[Bob]: Yes!\n"
        for shift in range(26):
            with self.subTest(shift=shift):
                self.assertEqual(self.cipher.decrypt(self.cipher.encrypt(text, shift), shift), text)


class TestRandomShift(unittest.TestCase):
    def test_always_between_1_and_25(self):
        cipher = RotatingCaesarCipher(random.Random(0))
        for _ in range(500):
            self.assertIn(cipher.random_shift(), range(1, 26))

    def test_never_repeats_previous_shift(self):
        cipher = RotatingCaesarCipher(random.Random(1))
        for previous in range(1, 26):
            for _ in range(50):
                self.assertNotEqual(cipher.random_shift(previous), previous)

    def test_every_other_shift_is_possible(self):
        cipher = RotatingCaesarCipher(random.Random(2))
        seen = {cipher.random_shift(7) for _ in range(2000)}
        self.assertEqual(seen, set(range(1, 26)) - {7})

    def test_default_uses_system_randomness(self):
        self.assertIsInstance(RotatingCaesarCipher()._rng, random.SystemRandom)


if __name__ == "__main__":
    unittest.main()
