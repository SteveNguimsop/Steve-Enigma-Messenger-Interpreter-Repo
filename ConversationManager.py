"""Reads, decrypts, appends to, encrypts and saves user-to-user conversations.

Group Project 2 removed the master list from the message repo (UEMR), so a
conversation "exists" exactly when its [User1]-[User2].txt file exists in the
repo folder.

File format (from Individual Project 1), one message per line, then the whole
file is encrypted with a Rotating Caesar Cipher using a random shift:

    [Alice]: Hi Bob
    [Bob]: Hey Alice
"""

from pathlib import Path

from CipherBreaker import CipherBreaker
from RotatingCaesarCipher import RotatingCaesarCipher
from UserValidator import UserValidator


class ConversationManager:
    def __init__(self, repo_path: str | Path,
                 cipher: RotatingCaesarCipher | None = None,
                 breaker: CipherBreaker | None = None,
                 validator: UserValidator | None = None):
        self.repo_path = Path(repo_path).resolve()
        self.cipher = cipher or RotatingCaesarCipher()
        self.breaker = breaker or CipherBreaker(self.cipher)
        self.validator = validator or UserValidator()
        self.current_filename: str | None = None
        self.current_text = ""
        self.last_shift: int | None = None

    def conversation_path(self, filename: str) -> Path:
        self.validator.users_from_filename(filename)  # rejects bad names / paths
        return self.repo_path / filename

    def exists(self, filename: str) -> bool:
        return self.conversation_path(filename).is_file()

    @staticmethod
    def match_filename(filename: str, existing: list[str]) -> str | None:
        """Find filename among existing names, ignoring upper/lower case.

        An exact match wins; otherwise the alphabetically first case-insensitive
        match is used, so "juan-steve.txt" finds "Juan-Steve.txt".
        """
        if filename in existing:
            return filename
        matches = sorted(name for name in existing if name.lower() == filename.lower())
        return matches[0] if matches else None

    def find_conversation(self, a: str, b: str) -> str:
        """Filename for a and b, reusing an existing file's exact capitalization."""
        filename = self.validator.conversation_filename(a, b)
        if not self.repo_path.is_dir():
            return filename
        existing = [path.name for path in self.repo_path.iterdir() if path.is_file()]
        return self.match_filename(filename, existing) or filename

    def open_conversation(self, a: str, b: str) -> str:
        """Return the decrypted conversation between a and b.

        Usernames are matched without regard to case, so "juan" and "Juan" open
        the same conversation. Creates an empty conversation file if none exists yet.
        """
        filename = self.find_conversation(a, b)
        path = self.conversation_path(filename)

        if path.is_file():
            ciphertext = self.read_file(path)
            speakers = self.validator.users_from_filename(filename)
            self.last_shift, self.current_text = self.breaker.crack(ciphertext, speakers)
        else:
            self.repo_path.mkdir(parents=True, exist_ok=True)
            self.write_file(path, "")
            self.last_shift, self.current_text = None, ""

        self.current_filename = filename
        return self.current_text

    def speaker_name(self, user: str) -> str:
        """Spell user the way the open conversation's filename does ("juan" -> "Juan")."""
        if self.current_filename:
            for name in self.validator.users_from_filename(self.current_filename):
                if name.lower() == user.lower():
                    return name
        return user

    def append_message(self, user: str, text: str) -> str:
        """Add "[user]: text" to the end of the open conversation."""
        if not self.validator.is_valid(user):
            raise ValueError(f"Invalid username: {user!r}")
        user = self.speaker_name(user)
        message = " ".join(text.split())  # one line, no stray whitespace
        if not message:
            raise ValueError("Message cannot be empty.")

        conversation = self.current_text
        if conversation and not conversation.endswith("\n"):
            conversation += "\n"
        self.current_text = f"{conversation}[{user}]: {message}\n"
        return self.current_text

    def save_conversation(self, filename: str, text: str) -> int:
        """Encrypt text with a new random shift and write it. Returns the shift."""
        shift = self.cipher.random_shift(self.last_shift)
        self.write_file(self.conversation_path(filename), self.cipher.encrypt(text, shift))
        self.last_shift = shift
        return shift

    @staticmethod
    def read_file(path: Path) -> str:
        with open(path, encoding="utf-8", newline="") as file:
            return file.read().replace("\r\n", "\n")

    @staticmethod
    def write_file(path: Path, content: str) -> None:
        # Always "\n" so files are identical on Windows, macOS and Linux.
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(content)
