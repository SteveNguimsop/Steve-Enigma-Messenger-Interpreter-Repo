import re

USERNAME_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9]*")
FILENAME_PATTERN = re.compile(r"([A-Za-z][A-Za-z0-9]*)-([A-Za-z][A-Za-z0-9]*)\.txt")


class UserValidator:
    def is_valid(self, username: str) -> bool:
        """Alphanumeric only, and the first character must be a letter."""
        return isinstance(username, str) and USERNAME_PATTERN.fullmatch(username) is not None

    def conversation_filename(self, a: str, b: str) -> str:
        """Build [User1]-[User2].txt with User1 alphabetically before User2."""
        if not self.is_valid(a) or not self.is_valid(b):
            raise ValueError(
                "Usernames must start with a letter and contain only letters and digits."
            )
        if a.lower() == b.lower():
            raise ValueError("You cannot start a conversation with yourself.")

        first, second = sorted((a, b), key=lambda name: (name.lower(), name))
        return f"{first}-{second}.txt"

    def users_from_filename(self, filename: str) -> tuple[str, str]:
        """Inverse of conversation_filename: 'Alice-Bob.txt' -> ('Alice', 'Bob')."""
        match = FILENAME_PATTERN.fullmatch(filename)
        if match is None:
            raise ValueError(f"Not a user-to-user filename: {filename!r}")
        return match.group(1), match.group(2)
