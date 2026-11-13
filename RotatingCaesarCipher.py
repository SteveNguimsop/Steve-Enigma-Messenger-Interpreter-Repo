"""Rotating Caesar Cipher (RCC) from Individual Project 2.

For the k-th alphabetic letter of a message (k starting at 1), the letter is
shifted k * n positions to the right, wrapping around the alphabet. Case is
preserved and every non-alphabetic character (digits, punctuation, spaces,
newlines) is copied unchanged and does not advance the rotation.

    RCC_encrypt("Hello", 2) -> "Jirty"
    RCC_decrypt("Jirty", 2) -> "Hello"
"""

import random

ALPHABET_SIZE = 26


class RotatingCaesarCipher:
    MIN_SHIFT = 1
    MAX_SHIFT = ALPHABET_SIZE - 1

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.SystemRandom()

    def random_shift(self, previous_shift: int | None = None) -> int:
        """Return a random shift in 1..25 that differs from previous_shift.

        Shift 0 (and any multiple of 26) is excluded because it would leave
        the message unencrypted.
        """
        shifts = [
            shift
            for shift in range(self.MIN_SHIFT, self.MAX_SHIFT + 1)
            if previous_shift is None or shift != previous_shift % ALPHABET_SIZE
        ]
        return self._rng.choice(shifts)

    def encrypt(self, text: str, shift: int) -> str:
        return self._rotate(text, shift, direction=1)

    def decrypt(self, text: str, shift: int) -> str:
        return self._rotate(text, shift, direction=-1)

    # Names used in Individual Project 2, kept so the original tests still run.
    def RCC_encrypt(self, msg: str, shift: int) -> str:
        return self.encrypt(msg, shift)

    def RCC_decrypt(self, msg: str, shift: int) -> str:
        return self.decrypt(msg, shift)

    @staticmethod
    def _rotate(text: str, shift: int, direction: int) -> str:
        result = []
        k = 0
        for ch in text:
            if ch.isascii() and ch.isalpha():
                k += 1
                base = ord("A") if ch.isupper() else ord("a")
                offset = (ord(ch) - base + direction * k * shift) % ALPHABET_SIZE
                result.append(chr(base + offset))
            else:
                result.append(ch)
        return "".join(result)
