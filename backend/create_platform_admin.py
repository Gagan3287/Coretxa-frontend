#!/usr/bin/env python3
"""
create_platform_admin.py -- CLI utility to provision a platform super-admin.

Usage:
    python create_platform_admin.py [--force]

Prompts interactively for email and password.
Passwords are masked using getpass and never logged or written to disk.
Refuses to create a second platform admin unless --force is passed.
"""
import argparse
import asyncio
import getpass
import re
import sys
from sqlalchemy import func, select

from app.core.database import engine, platform_session
from app.core.security import hash_password
from app.models.platform_admin import PlatformAdmin

EMAIL_REGEX = re.compile(r"^[^@]+@[^@]+\.[^@]+$")


async def create_admin(force: bool = False) -> None:
    # 1. Prompt for email
    email = input("Admin email: ").strip()
    if not email or not EMAIL_REGEX.match(email):
        print("Error: A valid email address is required.", file=sys.stderr)
        sys.exit(1)

    # 2. Prompt for password securely
    password = getpass.getpass("Admin password: ")
    if not password or len(password) < 8:
        print("Error: Password must be at least 8 characters long.", file=sys.stderr)
        sys.exit(1)

    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Error: Passwords do not match.", file=sys.stderr)
        sys.exit(1)

    # 3. Hash password with app.core.security
    pwd_hash = hash_password(password)

    # Clear plain password variables from memory
    del password
    del confirm

    # 4. Insert via platform_session()
    async with platform_session() as session:
        # Check count of existing admins
        count_res = await session.execute(
            select(func.count()).select_from(PlatformAdmin)
        )
        admin_count = count_res.scalar_one()

        if admin_count > 0 and not force:
            print(
                f"Error: {admin_count} platform admin(s) already exist. "
                "Refusing to create another admin without --force.",
                file=sys.stderr,
            )
            sys.exit(1)

        # Check if email is already taken
        email_res = await session.execute(
            select(PlatformAdmin).where(PlatformAdmin.email == email)
        )
        existing = email_res.scalar_one_or_none()
        if existing:
            print(f"Error: Platform admin with email '{email}' already exists.", file=sys.stderr)
            sys.exit(1)

        admin = PlatformAdmin(email=email, password_hash=pwd_hash)
        session.add(admin)

    print(f"Platform admin '{email}' created successfully.")


async def _run(force: bool) -> None:
    try:
        await create_admin(force=force)
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description="Create Cortexa Platform Super-Admin")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow creating additional platform admins if one already exists",
    )
    args = parser.parse_args()

    asyncio.run(_run(force=args.force))


if __name__ == "__main__":
    main()
