from src.db.database import SessionLocal
from src.db.seeders.reference_data import seed_reference_data


def main() -> None:
    with SessionLocal.begin() as session:
        created = seed_reference_data(session)

    print(
        "Demo seed complete: "
        f"{created['users']} users, "
        f"{created['auth_accounts']} auth accounts, "
        f"{created['verification_tokens']} verification tokens added."
    )


if __name__ == "__main__":
    main()