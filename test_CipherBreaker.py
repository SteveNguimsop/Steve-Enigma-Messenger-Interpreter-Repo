import tempfile
import unittest
from pathlib import Path

from CipherBreaker import CipherBreaker
from RotatingCaesarCipher import RotatingCaesarCipher


class TestCrack(unittest.TestCase):
    def setUp(self):
        self.cipher = RotatingCaesarCipher()
        self.breaker = CipherBreaker(self.cipher)

    def assertCracks(self, plaintext, speakers=()):
        for shift in range(1, 26):
            with self.subTest(shift=shift):
                found_shift, found_text = self.breaker.crack(
                    self.cipher.encrypt(plaintext, shift), speakers)
                self.assertEqual(found_text, plaintext)
                self.assertEqual(found_shift, shift)

    def test_conversation_with_speakers(self):
        self.assertCracks("[Alice]: Did you receive my message?\n[Bob]: Yes I did!\n",
                          ("Alice", "Bob"))

    def test_single_short_message(self):
        self.assertCracks("[Amy]: hi\n", ("Amy", "Zed"))

    def test_message_of_only_unknown_words(self):
        self.assertCracks("[Steve]: xqzv brrr\n", ("Kim", "Steve"))

    def test_plain_english_without_format(self):
        self.assertCracks("Meet me at the library after class tomorrow")

    def test_no_letters(self):
        self.assertEqual(self.breaker.crack("123 !?\n"), (0, "123 !?\n"))

    def test_empty(self):
        self.assertEqual(self.breaker.crack(""), (0, ""))


class TestScores(unittest.TestCase):
    def setUp(self):
        self.breaker = CipherBreaker()

    def test_format_score_counts_matching_lines(self):
        text = "[Amy]: hi\n[Bob]: hey\nrandom line\n"
        self.assertAlmostEqual(self.breaker.format_score(text), 2 / 3)

    def test_format_score_restricts_to_speakers(self):
        text = "[Amy]: hi\n[Eve]: hey\n"
        self.assertAlmostEqual(self.breaker.format_score(text, ("Amy", "Bob")), 1 / 2)

    def test_format_score_speakers_case_insensitive(self):
        self.assertEqual(self.breaker.format_score("[amy]: hi\n", ("Amy",)), 1.0)

    def test_format_score_empty(self):
        self.assertEqual(self.breaker.format_score("\n\n"), 0.0)

    def test_word_score(self):
        self.assertAlmostEqual(self.breaker.word_score("hello xyzzy"), 0.5)
        self.assertEqual(self.breaker.word_score("123"), 0.0)

    def test_chi_squared_prefers_english(self):
        english = self.breaker.chi_squared("the quick brown fox jumps over the lazy dog")
        gibberish = self.breaker.chi_squared("qzxj qzxj vkqz jjxq")
        self.assertLess(english, gibberish)
        self.assertEqual(self.breaker.chi_squared("!!!"), 0.0)


class TestWordList(unittest.TestCase):
    def test_default_word_list_loaded(self):
        words = CipherBreaker().words
        self.assertGreater(len(words), 200)
        self.assertIn("hello", words)
        self.assertFalse(any(w.startswith("#") for w in words))

    def test_custom_word_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "words.txt"
            path.write_text("# comment\nApple\n\n banana \n", encoding="utf-8")
            self.assertEqual(CipherBreaker.load_words(path), {"apple", "banana"})


if __name__ == "__main__":
    unittest.main()
