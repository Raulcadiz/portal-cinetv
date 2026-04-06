"""
Seed script: creates the first admin user from environment variables.

Usage:
    python scripts/seed_admin.py

Environment variables (or .env file):
    ADMIN_USERNAME  — default: admin
    ADMIN_PASSWORD  — required (will abort if still the default placeholder)
"""
import asyncio
import os
import sys
import uuid

# Ensure src/ is on the Python path when run from the project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select

from src.api.middlewares.auth import hash_password
from src.api.models.admin_user import AdminUser
from src.core.config import settings
from src.core.database import AsyncSessionLocal, create_tables


async def seed() -> None:
    await create_tables()

    username = settings.admin_username
    password = settings.admin_password

    if password in ("CHANGE_ME_IN_PRODUCTION", "change_me_in_production"):
        print("ERROR: Set ADMIN_PASSWORD in .env before running seed.", file=sys.stderr)
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(AdminUser).where(AdminUser.username == username))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Admin user '{username}' already exists — skipping.")
            return

        admin = AdminUser(
            id=str(uuid.uuid4()),
            username=username,
            hashed_password=hash_password(password),
        )
        db.add(admin)
        await db.commit()
        print(f"Admin user '{username}' created successfully.")


if __name__ == "__main__":
    asyncio.run(seed())
