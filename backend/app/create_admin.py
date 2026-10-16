"""Add an admin account, or change an existing one's name and password.

    uv run python -m app.create_admin <username> "<Full Name>"
"""

import sys
from getpass import getpass

from .database import connect, init_db
from .security import hash_password


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    username, name = sys.argv[1].strip(), sys.argv[2].strip()
    password = getpass("Password: ")
    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")
    if password != getpass("Repeat password: "):
        sys.exit("Passwords don't match.")

    init_db()
    db = connect()
    with db:
        db.execute(
            """INSERT INTO admins (username, name, password_hash) VALUES (?, ?, ?)
               ON CONFLICT (username) DO UPDATE SET name = excluded.name,
                                                    password_hash = excluded.password_hash""",
            (username, name, hash_password(password)),
        )
        # Sign the account out everywhere so an old password stops working at once
        db.execute("DELETE FROM sessions WHERE username = ?", (username,))
    print(f"Saved admin account '{username}'.")


if __name__ == "__main__":
    main()
