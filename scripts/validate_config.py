#!/usr/bin/env python3
"""
Validate Oxide configuration files.

Usage:
    python scripts/validate_config.py
    python scripts/validate_config.py --config path/to/config.yaml
"""
import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from oxide.config.loader import load_config, load_model_profiles, ConfigError


def validate_config(config_path: Path | None = None):
    """Validate main configuration file."""
    print("="*60)
    print("Validating Configuration")
    print("="*60)

    if config_path:
        print(f"Config file: {config_path}")
    else:
        config_path = Path(__file__).parent.parent / "config" / "default.yaml"
        print(f"Config file: {config_path} (default)")

    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        return False

    print(f"✅ Config file exists\n")

    # Try to load and validate
    try:
        config = load_config(config_path)
        print(f"✅ Configuration is valid\n")

        # Print summary
        print("Services configured:")
        for service_name, service_config in config.services.items():
            enabled = "✅" if service_config.enabled else "❌"
            print(f"  {enabled} {service_name} ({service_config.type.value})")

        print(f"\nRouting rules: {len(config.routing_rules)}")
        for task_type in config.routing_rules.keys():
            print(f"  - {task_type}")

        print(f"\nExecution settings:")
        print(f"  Max parallel workers: {config.execution.max_parallel_workers}")
        print(f"  Timeout: {config.execution.timeout_seconds}s")
        print(f"  Streaming: {config.execution.streaming}")
        print(f"  Retry on failure: {config.execution.retry_on_failure}")

        print(f"\nLogging:")
        print(f"  Level: {config.logging.level}")
        print(f"  File: {config.logging.file}")
        print(f"  Console: {config.logging.console}")

        return True

    except ConfigError as e:
        print(f"❌ Configuration is invalid:\n   {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def validate_model_profiles():
    """Validate model profiles file."""
    print("\n" + "="*60)
    print("Validating Model Profiles")
    print("="*60)

    profiles_path = Path(__file__).parent.parent / "config" / "models.yaml"
    print(f"Profiles file: {profiles_path}")

    if not profiles_path.exists():
        print(f"❌ Profiles file not found: {profiles_path}")
        return False

    print(f"✅ Profiles file exists\n")

    try:
        profiles = load_model_profiles(profiles_path)
        print(f"✅ Model profiles are valid\n")

        print(f"Model profiles configured: {len(profiles.model_profiles)}")
        for model_name in profiles.model_profiles.keys():
            print(f"  - {model_name}")

        return True

    except ConfigError as e:
        print(f"❌ Model profiles are invalid:\n   {e}")
        return False

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Validate Oxide configuration")
    parser.add_argument(
        "--config",
        type=Path,
        help="Path to config file (default: config/default.yaml)"
    )

    args = parser.parse_args()

    print("🔬 Oxide Configuration Validator")
    print()

    # Validate main config
    config_valid = validate_config(args.config)

    # Validate model profiles
    profiles_valid = validate_model_profiles()

    # Summary
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if config_valid and profiles_valid:
        print("✅ All configuration files are valid!")
        return 0
    else:
        print("❌ Configuration validation failed")
        if not config_valid:
            print("   - Main configuration has errors")
        if not profiles_valid:
            print("   - Model profiles have errors")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
