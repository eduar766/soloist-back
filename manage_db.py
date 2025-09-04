#!/usr/bin/env python3
"""
Database management script for Soloist backend.
Handles database initialization, migrations, and seeding.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from alembic.config import Config
from alembic import command
from app.infrastructure.db.database import engine
from app.infrastructure.db.models import create_all_tables


def init_alembic():
    """Initialize Alembic if not already done."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    
    # Check if alembic has been initialized
    versions_dir = Path("app/infrastructure/db/migrations/versions")
    if not versions_dir.exists():
        print("Initializing Alembic...")
        versions_dir.mkdir(parents=True, exist_ok=True)
        command.init(alembic_cfg, "app/infrastructure/db/migrations")


def create_migration(message: str = "Auto-generated migration"):
    """Create a new migration."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    print(f"Creating migration: {message}")
    command.revision(alembic_cfg, message=message, autogenerate=True)


def run_migrations():
    """Run pending migrations."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    print("Running migrations...")
    command.upgrade(alembic_cfg, "head")


def rollback_migration():
    """Rollback last migration."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    print("Rolling back migration...")
    command.downgrade(alembic_cfg, "-1")


def reset_database():
    """Reset database - WARNING: This will drop all data!"""
    response = input("This will drop ALL data. Type 'yes' to continue: ")
    if response.lower() == 'yes':
        alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
        print("Resetting database...")
        command.downgrade(alembic_cfg, "base")
        command.upgrade(alembic_cfg, "head")
    else:
        print("Database reset cancelled.")


def show_current_revision():
    """Show current database revision."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    command.current(alembic_cfg)


def show_history():
    """Show migration history."""
    alembic_cfg = Config("app/infrastructure/db/migrations/alembic.ini")
    command.history(alembic_cfg)


def create_initial_migration():
    """Create the initial migration with all tables."""
    print("Creating initial migration...")
    create_migration("Initial migration - create all tables")


def main():
    """Main CLI function."""
    if len(sys.argv) < 2:
        print("Usage: python manage_db.py [command]")
        print("Commands:")
        print("  init           - Initialize Alembic")
        print("  create [msg]   - Create new migration")
        print("  migrate        - Run pending migrations")
        print("  rollback       - Rollback last migration") 
        print("  reset          - Reset database (WARNING: drops all data)")
        print("  current        - Show current revision")
        print("  history        - Show migration history")
        print("  initial        - Create initial migration")
        return

    command_name = sys.argv[1]
    
    if command_name == "init":
        init_alembic()
    elif command_name == "create":
        message = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "Auto-generated migration"
        create_migration(message)
    elif command_name == "migrate":
        run_migrations()
    elif command_name == "rollback":
        rollback_migration()
    elif command_name == "reset":
        reset_database()
    elif command_name == "current":
        show_current_revision()
    elif command_name == "history":
        show_history()
    elif command_name == "initial":
        create_initial_migration()
    else:
        print(f"Unknown command: {command_name}")


if __name__ == "__main__":
    main()