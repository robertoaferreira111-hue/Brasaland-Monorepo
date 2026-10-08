"""Optional demo user for local testing."""

from app.database import create_user, open_db, users_table
from app.models import RegisterUser


def main() -> None:
    db = open_db()
    try:
        table = users_table(db)
        try:
            profile = create_user(
                table,
                RegisterUser(email="staff@brasaland.com", password="demo-password"),
            )
        except ValueError:
            print("Seed user already exists.")
            return
        print(f"Seeded {profile.email}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
