"""
Secure one-time administrative bootstrap CLI command.
Usage:
    python -m scripts.bootstrap_admin --email admin@example.com [--password SecurePassword123] [--name "Super Admin"]
If password is not provided, a cryptographically secure random password is generated and displayed once.
"""
import argparse
import asyncio
import secrets
import string
import sys
from sqlalchemy import select

from app.database.base import AsyncSessionLocal
from app.models.user import User, UserRole
from app.core.security import hash_password


def generate_secure_password(length: int = 24) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.isupper() for c in pwd)
            and any(c.islower() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in "!@#$%^&*()-_=+" for c in pwd)):
            return pwd


async def bootstrap_admin(email: str, password: str | None, name: str) -> None:
    async with AsyncSessionLocal() as db:
        # Check if email exists
        res = await db.execute(select(User).where(User.email == email.lower()))
        existing = res.scalar_one_or_none()
        if existing:
            print(f"Error: A user with email '{email}' already exists (Role: {existing.role.value}).", file=sys.stderr)
            sys.exit(1)

        auto_generated = False
        if not password:
            password = generate_secure_password(24)
            auto_generated = True

        admin = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            full_name=name,
            role=UserRole.SUPER_ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        await db.refresh(admin)

        print("=" * 60)
        print("AgentHub Administrator Bootstrap Successful")
        print("=" * 60)
        print(f"ID:       {admin.id}")
        print(f"Email:    {admin.email}")
        print(f"Name:     {admin.full_name}")
        print(f"Role:     {admin.role.value}")
        if auto_generated:
            print(f"Password: {password}")
            print("\nIMPORTANT: Copy this password now. It is hashed and cannot be retrieved.")
        else:
            print("Password: [Supplied by operator]")
        print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Bootstrap initial AgentHub super-admin")
    parser.add_argument("--email", required=True, help="Administrator email address")
    parser.add_argument("--password", required=False, help="Administrator password (optional, auto-generated if omitted)")
    parser.add_argument("--name", default="Platform Super Admin", help="Administrator full name")

    args = parser.parse_args()
    asyncio.run(bootstrap_admin(args.email, args.password, args.name))


if __name__ == "__main__":
    main()
