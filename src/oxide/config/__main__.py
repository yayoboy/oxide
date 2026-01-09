"""
CLI tool for Oxide configuration migration.

Usage:
    python -m oxide.config.migration           # Migrate with defaults
    python -m oxide.config.migration --verify  # Verify migration
    python -m oxide.config.migration --export output.yaml  # Export DB to YAML
"""
import argparse
import sys
from pathlib import Path

from .migration import ConfigMigration, migrate_config
from ..utils.logging import setup_logging, logger


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Oxide Configuration Migration Tool",
        epilog="Migrates configuration from YAML to SQLite database"
    )

    parser.add_argument(
        "--yaml",
        type=Path,
        help="Path to YAML config file (default: config/default.yaml)"
    )

    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Don't create backup of YAML file"
    )

    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip configuration validation"
    )

    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify existing migration (compare YAML vs DB)"
    )

    parser.add_argument(
        "--export",
        type=Path,
        metavar="OUTPUT_YAML",
        help="Export database configuration to YAML file"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    log_level = "DEBUG" if args.verbose else "INFO"
    setup_logging(level=log_level, console=True)

    # Default YAML path
    yaml_path = args.yaml
    if yaml_path is None:
        yaml_path = Path(__file__).parent.parent.parent.parent / "config" / "default.yaml"

    migration = ConfigMigration(yaml_path)

    # Handle different operations
    if args.verify:
        # Verify migration
        logger.info("Verifying migration...")
        result = migration.verify_migration()

        if result.get("perfect_match"):
            logger.info("✅ Migration verification: PASSED")
            logger.info(f"   Services: {result['services']['db_count']}")
            logger.info(f"   Routing rules: {result['routing_rules']['db_count']}")
            sys.exit(0)
        else:
            logger.warning("⚠️  Migration verification: FAILED")
            logger.warning(f"   Services - YAML: {result['services']['yaml_count']}, DB: {result['services']['db_count']}")
            logger.warning(f"   Routing rules - YAML: {result['routing_rules']['yaml_count']}, DB: {result['routing_rules']['db_count']}")

            if result['services'].get('only_in_yaml'):
                logger.warning(f"   Services only in YAML: {result['services']['only_in_yaml']}")
            if result['services'].get('only_in_db'):
                logger.warning(f"   Services only in DB: {result['services']['only_in_db']}")

            sys.exit(1)

    elif args.export:
        # Export to YAML
        logger.info(f"Exporting database to YAML: {args.export}")
        result = migration.export_db_to_yaml(args.export)

        if result['status'] == 'success':
            logger.info(f"✅ Exported to: {result['output_path']}")
            sys.exit(0)
        else:
            logger.error(f"❌ Export failed: {result.get('message')}")
            sys.exit(1)

    else:
        # Migrate YAML to DB
        logger.info("=" * 60)
        logger.info("Oxide Configuration Migration Tool")
        logger.info("=" * 60)
        logger.info(f"Source YAML: {yaml_path}")
        logger.info(f"Target DB: ~/.oxide/config.db")
        logger.info("")

        result = migrate_config(
            yaml_path=yaml_path,
            backup=not args.no_backup,
            validate=not args.no_validate
        )

        logger.info("")
        logger.info("=" * 60)

        if result['status'] == 'success':
            logger.info("✅ Migration completed successfully!")
            logger.info("")
            logger.info("Statistics:")
            logger.info(f"  Services migrated: {result['services_migrated']}")
            logger.info(f"  Routing rules migrated: {result['routing_rules_migrated']}")
            logger.info(f"  Execution settings: {result['execution_settings']}")

            if result.get('backup_path'):
                logger.info(f"  YAML backup: {result['backup_path']}")

            logger.info("")
            logger.info("Next steps:")
            logger.info("  1. Verify migration: python -m oxide.config.migration --verify")
            logger.info("  2. Start Oxide normally - it will use SQLite automatically")
            logger.info("  3. Use Web UI to manage configuration")
            logger.info("")
            logger.info("To rollback: Delete ~/.oxide/config.db and restart")

            sys.exit(0)
        else:
            logger.error(f"❌ Migration failed: {result.get('message')}")
            sys.exit(1)


if __name__ == "__main__":
    main()
