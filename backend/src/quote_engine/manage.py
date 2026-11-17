"""Management commands, run on the server or locally as ``uv run python -m quote_engine.manage``:

    migrate
    create-workshop "Name" --small-max-mm2 N --standard-max-mm2 N [--currency EUR] [--language en]
    invite <workshop-id> --role owner|staff
    create-user <workshop-id> <email> --role owner|staff
    seed-demo
    wipe-demo
    purge-sandboxes

A new workshop's first owner joins through the invite link ``create-workshop`` prints; nobody
else ever sees their password. ``create-user`` remains for scripts and local work: its password
is read from the terminal (never from the command line, so it stays out of the shell history),
or from ``QUOTE_ENGINE_NEW_PASSWORD``. Passwords are never printed, except the generated demo
password, which is meant to be shown on the demo's login page.
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
from quote_engine.services import auth, demo, sandbox, workshops
from quote_engine.settings import get_settings

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


def _invite(db_workshop_id: uuid.UUID, role: str) -> None:
    for db in db_session():
        created = workshops.create_invite(db, db_workshop_id, role, None)
        print(f"invite for a new {role} (valid {workshops.INVITE_DAYS} days, shown once):")
        print(workshops.invite_link(get_settings().public_url, created.token))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m quote_engine.manage")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("migrate", help="apply database migrations")
    new_workshop = commands.add_parser(
        "create-workshop", help="add a workshop and invite its owner"
    )
    new_workshop.add_argument("name")
    new_workshop.add_argument("--small-max-mm2", type=int, required=True)
    new_workshop.add_argument("--standard-max-mm2", type=int, required=True)
    new_workshop.add_argument("--currency", choices=workshops.CURRENCIES, default="EUR")
    new_workshop.add_argument("--language", choices=workshops.LANGUAGES, default="en")
    invite = commands.add_parser("invite", help="a one-time link for a new person")
    invite.add_argument("workshop_id", type=uuid.UUID)
    invite.add_argument("--role", choices=auth.ROLES, required=True)
    new_user = commands.add_parser("create-user", help="add a login directly (scripts, local)")
    new_user.add_argument("workshop_id", type=uuid.UUID)
    new_user.add_argument("email")
    new_user.add_argument("--role", choices=auth.ROLES, required=True)
    commands.add_parser("seed-demo", help="wipe and recreate the demo workshop")
    commands.add_parser("wipe-demo", help="delete the demo workshop")
    commands.add_parser("purge-sandboxes", help="delete expired 'Try it' sandboxes")
    args = parser.parse_args(argv)

    if args.command == "migrate":
        migrate()
        return 0
    try:
        if args.command == "invite":
            _invite(args.workshop_id, args.role)
            return 0
        for db in db_session():
            if args.command == "create-workshop":
                workshop = workshops.create_workshop(
                    db,
                    args.name,
                    args.small_max_mm2,
                    args.standard_max_mm2,
                    currency=args.currency,
                    language=args.language,
                )
                created = workshops.create_invite(db, workshop.id, auth.ROLE_OWNER, None)
                print(f"workshop {workshop.id}")
                print(f"owner invite (valid {workshops.INVITE_DAYS} days, shown once):")
                print(workshops.invite_link(get_settings().public_url, created.token))
            elif args.command == "create-user":
                user = workshops.create_user(
                    db, args.workshop_id, args.email, _password(), args.role
                )
                print(f"user {user.id} ({user.role})")
            elif args.command == "seed-demo":
                demo.wipe_demo(db)
                workshop, password = demo.seed_demo(db, datetime.now(UTC).date())
                print(f"demo workshop {workshop.id}: {demo.DEMO_EMAIL} / {password}")
            elif args.command == "wipe-demo":
                print(f"removed {demo.wipe_demo(db)} demo workshop(s)")
            elif args.command == "purge-sandboxes":
                print(f"removed {sandbox.purge_expired(db)} expired sandbox(es)")
    except workshops.SetupError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
