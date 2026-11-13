"""Recovers the random shift of an RCC-encrypted conversation by brute force.

The shift is never stored in the message repo, so the reader tries every
shift (there are only 26) and keeps the candidate that looks most like a real
conversation. Candidates are ranked by, in order:

1. Format: the fraction of lines that start with "[<speaker>]: ", where the
   speakers are the two users in the filename (a near-certain signal).
2. Words: the fraction of words found in english_words.txt.
3. Letters: how close the letter frequencies are to normal English
   (a chi-squared distance, smaller is better).
"""

import re
from pathlib import Path

from RotatingCaesarCipher import ALPHABET_SIZE, RotatingCaesarCipher

DEFAULT_WORDS_PATH = Path(__file__).resolve().parent / "english_words.txt"

# Relative frequency (%) of each letter A-Z in English text.
ENGLISH_LETTER_FREQ = (
    8.17, 1.49, 2.78, 4.25, 12.70, 2.23, 2.02, 6.09, 6.97, 0.15, 0.77, 4.03, 2.41,
    6.75, 7.51, 1.93, 0.10, 5.99, 6.33, 9.06, 2.76, 0.98, 2.36, 0.15, 1.97, 0.07,
)

WORD_PATTERN = re.compile(r"[A-Za-z]+")
SPEAKER_PATTERN = re.compile(r"^\[([A-Za-z][A-Za-z0-9]*)\]: ")


class CipherBreaker:
    def __init__(self, cipher: RotatingCaesarCipher | None = None,
                 words_path: str | Path = DEFAULT_WORDS_PATH):
        self.cipher = cipher or RotatingCaesarCipher()
        self.words = self.load_words(words_path)

    @staticmethod
    def load_words(path: str | Path) -> frozenset[str]:
        with open(path, encoding="utf-8") as file:
            return frozenset(
                line.strip().lower() for line in file
                if line.strip() and not line.startswith("#")
            )

    def crack(self, ciphertext: str, speakers: tuple[str, ...] = ()) -> tuple[int, str]:
        """Return (shift, plaintext) for the most plausible shift."""
        best_shift, best_plain, best_score = 0, ciphertext, None
        for shift in range(ALPHABET_SIZE):
            plain = self.cipher.decrypt(ciphertext, shift)
            score = self.score(plain, speakers)
            if best_score is None or score > best_score:
                best_shift, best_plain, best_score = shift, plain, score
        return best_shift, best_plain

    def score(self, text: str, speakers: tuple[str, ...] = ()) -> tuple[float, float, float]:
        """Higher tuples are more likely to be the real plaintext."""
        return (
            self.format_score(text, speakers),
            self.word_score(text),
            -self.chi_squared(text),
        )

    @staticmethod
    def format_score(text: str, speakers: tuple[str, ...] = ()) -> float:
        lines = [line for line in text.splitlines() if line.strip()]
        if not lines:
            return 0.0
        allowed = {s.lower() for s in speakers}
        matches = 0
        for line in lines:
            match = SPEAKER_PATTERN.match(line)
            if match and (not allowed or match.group(1).lower() in allowed):
                matches += 1
        return matches / len(lines)

    def word_score(self, text: str) -> float:
        words = [w.lower() for w in WORD_PATTERN.findall(text)]
        if not words:
            return 0.0
        return sum(w in self.words for w in words) / len(words)

    @staticmethod
    def chi_squared(text: str) -> float:
        counts = [0] * ALPHABET_SIZE
        for ch in text:
            if ch.isascii() and ch.isalpha():
                counts[ord(ch.lower()) - ord("a")] += 1
        total = sum(counts)
        if total == 0:
            return 0.0
        result = 0.0
        for observed, percent in zip(counts, ENGLISH_LETTER_FREQ):
            expected = total * percent / 100
            result += (observed - expected) ** 2 / expected
        return result
