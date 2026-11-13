"""Management commands, run on the server or locally as ``uv run python -m quote_engine.manage``:

    migrate
    create-workshop "Name" --small-max-mm2 N --standard-max-mm2 N
    create-user <workshop-id> <email> --role owner|admin
    seed-demo
    wipe-demo

A password is read from the terminal (never from the command line, so it stays out of the shell
history), or from ``QUOTE_ENGINE_NEW_PASSWORD`` for scripts. Passwords are never printed, except
the generated demo password, which is meant to be shown on the demo's login page.
"""

import argparse
import getpass
import os
import sys
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config

from quote_engine.db.session import db_session
from quote_engine.services import demo, workshops

MIGRATIONS = Path(__file__).with_name("migrations")
PASSWORD_ENV = "QUOTE_ENGINE_NEW_PASSWORD"  # noqa: S105  (the variable's name, not a password)


def migrate() -> None:
    """Bring the database schema up to the newest migration."""
    config = Config()
    config.set_main_option("script_location", str(MIGRATIONS))
    command.upgrade(config, "head")


def _password() -> str:
    from_env = os.environ.get(PASSWORD_ENV)
    if from_env:
        return from_env
    first = getpass.getpass("Password (at least 12 characters): ")
    if first != getpass.getpass("Same password again: "):
        raise workshops.SetupError("the two passwords differ")
    return first


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m quote_engine.manage")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply database migrations")
    new_workshop = commands.add_parser("create-workshop", help="add a workshop with its settings")
    new_workshop.add_argument("name")
    new_workshop.add_argument("--small-max-mm2", type=int, required=True)
    new_workshop.add_argument("--standard-max-mm2", type=int, required=True)
    new_user = commands.add_parser("create-user", help="add a login to a workshop")
    new_user.add_argument("workshop_id", type=uuid.UUID)
    new_user.add_argument("email")
    new_user.add_argument("--role", choices=("owner", "admin"), required=True)
    commands.add_parser("seed-demo", help="wipe and recreate the demo workshop")
    commands.add_parser("wipe-demo", help="delete the demo workshop")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        migrate()
        return 0
    try:
        for db in db_session():
            if args.command == "create-workshop":
                workshop = workshops.create_workshop(
                    db, args.name, args.small_max_mm2, args.standard_max_mm2
                )
                print(f"workshop {workshop.id}")
            elif args.command == "create-user":
                created = workshops.create_user(
                    db, args.workshop_id, args.email, _password(), args.role
                )
                print(f"user {created.user.id} ({created.user.role})")
                if created.totp_uri:
                    print("Add this to the authenticator app now; it is not shown again:")
                    print(created.totp_uri)
            elif args.command == "seed-demo":
                demo.wipe_demo(db)
                workshop, password = demo.seed_demo(db, datetime.now(UTC).date())
                print(f"demo workshop {workshop.id}: {demo.DEMO_EMAIL} / {password}")
            elif args.command == "wipe-demo":
                print(f"removed {demo.wipe_demo(db)} demo workshop(s)")
    except workshops.SetupError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
