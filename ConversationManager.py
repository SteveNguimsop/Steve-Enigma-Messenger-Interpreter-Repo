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

    def open_conversation(self, a: str, b: str) -> str:
        """Return the decrypted conversation between a and b.

        Creates an empty conversation file if none exists yet.
        """
        filename = self.validator.conversation_filename(a, b)
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

    def append_message(self, user: str, text: str) -> str:
        """Add "[user]: text" to the end of the open conversation."""
        if not self.validator.is_valid(user):
            raise ValueError(f"Invalid username: {user!r}")
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
