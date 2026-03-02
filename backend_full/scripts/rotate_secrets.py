from __future__ import annotations

import argparse
from secrets import token_hex, token_urlsafe

from app.infrastructure.db.session import SessionLocal
from app.models.models import Terminal


def rotate_terminal_secrets(*, dry_run: bool) -> list[tuple[str, str]]:
    with SessionLocal() as session:
        terminals = session.query(Terminal).order_by(Terminal.id.asc()).all()
        rotated: list[tuple[str, str]] = []
        for terminal in terminals:
            new_secret = token_urlsafe(48)
            rotated.append((terminal.terminal_id, new_secret))
            if not dry_run:
                terminal.secret_hash = new_secret
        if not dry_run:
            session.commit()
        return rotated


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate and rotate JWT/DB/HMAC secrets")
    parser.add_argument(
        "--apply-terminal-secrets",
        action="store_true",
        help="Write new random secrets to terminal.secret_hash in DB",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not persist terminal secret updates",
    )
    args = parser.parse_args()

    jwt_secret = token_urlsafe(64)
    postgres_password = token_hex(24)
    simple_postgres_password = token_hex(24)

    print("# Put these values into .env")
    print(f"JWT_SECRET_KEYS={jwt_secret}")
    print(f"POSTGRES_PASSWORD={postgres_password}")
    print(f"SIMPLE_POSTGRES_PASSWORD={simple_postgres_password}")

    if args.apply_terminal_secrets:
        rotated = rotate_terminal_secrets(dry_run=args.dry_run)
        mode = "DRY-RUN" if args.dry_run else "APPLIED"
        print(f"\n# Terminal secrets ({mode})")
        if not rotated:
            print("No terminals found")
        for terminal_id, secret in rotated:
            print(f"{terminal_id}={secret}")


if __name__ == "__main__":
    main()
