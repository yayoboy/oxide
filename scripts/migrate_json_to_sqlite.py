#!/usr/bin/env python3
"""
Migrate Oxide task storage from JSON to SQLite.

This script migrates existing JSON task data to the new high-performance
SQLite storage backend.

Usage:
    python scripts/migrate_json_to_sqlite.py [--dry-run] [--backup]

Options:
    --dry-run   Show what would be migrated without actually migrating
    --backup    Create backup of JSON file before migration
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from oxide.utils.task_storage_sqlite import TaskStorageSQLite
from oxide.utils.logging import logger


def main():
    """Main migration entry point."""
    parser = argparse.ArgumentParser(description="Migrate Oxide JSON storage to SQLite")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without actually migrating"
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup of JSON file before migration"
    )
    parser.add_argument(
        "--json-path",
        type=Path,
        default=Path.home() / ".oxide" / "tasks.json",
        help="Path to JSON storage file (default: ~/.oxide/tasks.json)"
    )
    parser.add_argument(
        "--sqlite-path",
        type=Path,
        default=Path.home() / ".oxide" / "tasks.db",
        help="Path to SQLite database file (default: ~/.oxide/tasks.db)"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("Oxide Storage Migration: JSON → SQLite")
    print("=" * 80)
    print()

    # Check if JSON file exists
    if not args.json_path.exists():
        print(f"❌ JSON file not found: {args.json_path}")
        print("   Nothing to migrate. You can start using SQLite directly.")
        return 0

    # Load JSON data
    print(f"📂 Loading JSON data from: {args.json_path}")
    try:
        with open(args.json_path, 'r') as f:
            json_tasks = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load JSON: {e}")
        return 1

    task_count = len(json_tasks)
    print(f"   Found {task_count} tasks")
    print()

    # Dry run mode
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print()
        print("Would migrate the following tasks:")
        print()

        for task_id, task in list(json_tasks.items())[:5]:
            status = task.get("status", "unknown")
            prompt = task.get("prompt", "")[:50]
            print(f"  • {task_id}: [{status}] {prompt}...")

        if task_count > 5:
            print(f"  ... and {task_count - 5} more tasks")

        print()
        print(f"Target database: {args.sqlite_path}")
        print()
        print("Run without --dry-run to perform actual migration")
        return 0

    # Backup JSON file
    if args.backup:
        backup_path = args.json_path.with_suffix(".json.backup")
        print(f"💾 Creating backup: {backup_path}")
        try:
            shutil.copy2(args.json_path, backup_path)
            print(f"   ✅ Backup created")
        except Exception as e:
            print(f"   ❌ Backup failed: {e}")
            print("   Migration aborted for safety")
            return 1
        print()

    # Perform migration
    print(f"🚀 Migrating to SQLite: {args.sqlite_path}")
    try:
        # Initialize SQLite storage
        sqlite_storage = TaskStorageSQLite(storage_path=args.sqlite_path)

        # Migrate data
        sqlite_storage.migrate_from_json(args.json_path)

        # Verify migration
        migrated_count = sqlite_storage.get_stats()["total"]

        print()
        print(f"✅ Migration completed successfully!")
        print(f"   Tasks migrated: {migrated_count}/{task_count}")

        if migrated_count != task_count:
            print(f"   ⚠️  Warning: Some tasks may have failed to migrate")
            print(f"   Check logs for details")

        # Close connection
        sqlite_storage.close()

    except Exception as e:
        print()
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

    print()
    print("=" * 80)
    print("Next Steps:")
    print("=" * 80)
    print()
    print("1. Verify migration by checking the SQLite database:")
    print(f"   sqlite3 {args.sqlite_path}")
    print("   SELECT COUNT(*) FROM tasks;")
    print()
    print("2. Update your configuration to use SQLite:")
    print("   In config/default.yaml, add:")
    print("   storage:")
    print("     backend: sqlite  # or 'json' to revert")
    print()
    print("3. (Optional) Remove old JSON file:")
    print(f"   rm {args.json_path}")
    if args.backup:
        print(f"   Keep backup at: {args.json_path.with_suffix('.json.backup')}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
