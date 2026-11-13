"""Enigma_Messenger: encrypted messaging between USAO students.

Usage:
    python MessengerApp.py [path-to-USAO-Enigma-Messenger-Repo]

The message repo defaults to ../USAO-Enigma-Messenger-Repo (a clone of
https://github.com/qtranokc/USAO-Enigma-Messenger-Repo next to this repo).
It can also be set with the UEMR_PATH environment variable.
"""

import os
import sys
from pathlib import Path
from typing import Callable

from ConversationManager import ConversationManager
from GitRepositoryManager import GitError, GitRepositoryManager
from UserValidator import UserValidator

DEFAULT_UEMR_PATH = Path(__file__).resolve().parent.parent / "USAO-Enigma-Messenger-Repo"


class MessengerApp:
    def __init__(self, repo_path: str | Path = DEFAULT_UEMR_PATH,
                 git: GitRepositoryManager | None = None,
                 conversations: ConversationManager | None = None,
                 validator: UserValidator | None = None,
                 input_func: Callable[[str], str] = input,
                 output_func: Callable[[str], None] = print):
        self.repo_path = Path(repo_path)
        self.git = git or GitRepositoryManager(self.repo_path)
        self.conversations = conversations or ConversationManager(self.repo_path)
        self.validator = validator or UserValidator()
        self.input = input_func
        self.output = output_func
        self.current_user: str | None = None
        self.recipient: str | None = None

    def run(self) -> None:
        self.output("=== Enigma Messenger ===")
        self.git.pull()

        self.current_user = self.prompt_username("Enter your username: ")
        self.select_recipient()

        history = self.conversations.open_conversation(self.current_user, self.recipient)
        filename = self.conversations.current_filename
        if history.strip():
            self.output(f"\n--- {filename} ---")
            self.output(history.rstrip("\n"))
            self.output("-" * (len(filename) + 8))
        else:
            self.output(f"\nStarting a new conversation: {filename}")

        self.send_message()

    def prompt_username(self, prompt: str) -> str:
        while True:
            name = self.input(prompt).strip()
            if self.validator.is_valid(name):
                return name
            self.output("Usernames must start with a letter and contain only letters and digits.")

    def select_recipient(self) -> str:
        while True:
            recipient = self.prompt_username("Who do you want to message? ")
            if recipient.lower() != self.current_user.lower():
                self.recipient = recipient
                return recipient
            self.output("You cannot message yourself. Choose another user.")

    def send_message(self) -> None:
        while True:
            message = self.input("Enter your message: ")
            if message.strip():
                break
            self.output("Message cannot be empty.")

        filename = self.conversations.current_filename
        updated = self.conversations.append_message(self.current_user, message)
        self.conversations.save_conversation(filename, updated)

        # The commit message is public, so it must not contain the message text.
        if self.git.commit_and_push([filename], f"Update {filename}"):
            self.output(f"Message sent and pushed to GitHub ({filename}).")
        else:
            self.output("Nothing changed, so nothing was pushed.")


def main(argv: list[str]) -> int:
    repo_path = Path(argv[1] if len(argv) > 1 else os.environ.get("UEMR_PATH", DEFAULT_UEMR_PATH))
    if not (repo_path / ".git").exists():
        print(f"Message repo not found at {repo_path}.\n"
              "Clone it first: git clone https://github.com/qtranokc/USAO-Enigma-Messenger-Repo")
        return 1
    try:
        MessengerApp(repo_path).run()
    except GitError as error:
        print(f"Git error: {error}")
        return 1
    except (KeyboardInterrupt, EOFError):
        print("\nGoodbye.")
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
