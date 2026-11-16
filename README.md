# Tatsiguia-Forero-Enigma-Messenger-Interpreter-Repo

Enigma_Messenger is an encrypted messenger for USAO students (CSCI-4163, Group Project 2, version 1).
Conversations are stored in the public
[USAO-Enigma-Messenger-Repo](https://github.com/qtranokc/USAO-Enigma-Messenger-Repo) (UEMR),
encrypted with a Rotating Caesar Cipher that uses a new random shift every time the file is saved.

## Group Members

- **Steve Nguimsop Tatsiguia:** Contributed the initial Enigma Messenger v1 implementation, existing unit tests, UML diagrams, and setup documentation.
- **Juan Forero:** Set up both repositories, ran selected local unit tests, added 100 English words and four UserValidator edge-case tests, and documented the group's contributions. Real communication testing is still pending.

## Setup

Requires Python 3.10+ and git. Clone both repos side by side:

```
git clone https://github.com/qtranokc/USAO-Enigma-Messenger-Repo
git clone https://github.com/SteveNguimsop/Tatsiguia-Forero-Enigma-Messenger-Interpreter-Repo
```

```
Software Engineering/
├── USAO-Enigma-Messenger-Repo/          <- messages (UEMR)
└── Tatsiguia-Forero-Enigma-Messenger-Interpreter-Repo/
```

## Run

```
cd Tatsiguia-Forero-Enigma-Messenger-Interpreter-Repo
python MessengerApp.py
```

If UEMR is somewhere else, pass its path: `python MessengerApp.py C:\path\to\USAO-Enigma-Messenger-Repo`,
or set the `UEMR_PATH` environment variable.

What happens when you run it:

1. Pulls the latest messages from GitHub.
2. Asks for your username and who you want to message. Usernames must be letters and digits and start with a letter.
3. Builds `[User1]-[User2].txt`, with the names in alphabetical order.
4. If the file exists, it is decrypted and printed. Otherwise an empty file is created.
5. Asks for your message, appends `[you]: message` to the conversation and re-encrypts the whole file with a new random shift.
6. Commits and pushes the file to GitHub. The commit message never contains your text.

## How decryption works without storing the shift

Shift *n* moves the k-th letter `k·n` places, so only the 26 values `0..25` are distinct.
`CipherBreaker` decrypts with every one of them and keeps the candidate that

1. has the most lines in the form `[User1]: ...` / `[User2]: ...` for the two users in the filename,
2. then has the most words found in `english_words.txt`,
3. then has letter frequencies closest to English.

## Files

| File | UML class / purpose |
|---|---|
| `MessengerApp.py` | `MessengerApp`, the program entry point and prompts |
| `UserValidator.py` | `UserValidator`, the username rules and the `[User1]-[User2].txt` filename |
| `ConversationManager.py` | `ConversationManager`, which opens, decrypts, appends, encrypts and saves |
| `GitRepositoryManager.py` | `GitRepositoryManager`, which runs `pull` and `commit_and_push` with git |
| `RotatingCaesarCipher.py` | `RotatingCaesarCipher`, the RCC from Individual Project 2 |
| `CipherBreaker.py` | `CipherBreaker`, which recovers the random shift by brute force |
| `english_words.txt` | Helper word list used by `CipherBreaker` |
| `test_*.py` | Unit test suite, one file per class |
| `UML/` | UML diagrams: the original from Group Project 1, plus the v1 update |

The v1 UML drops `MasterListManager` because Group Project 2 says UEMR holds *only* message files.
A conversation exists exactly when its file exists. `CipherBreaker` was added.

## Tests

```
python -m unittest -v
```

The git tests use a temporary local repository as a stand-in for GitHub. They never touch the real UEMR or the network.
