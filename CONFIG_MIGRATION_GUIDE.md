# Oxide Configuration Migration Guide

## Overview

Oxide now supports **database-backed configuration** management, allowing you to configure services, routing rules, and settings directly from the Web UI without editing YAML files.

## Features

- ✅ **SQLite Database Storage**: Thread-safe, concurrent access
- ✅ **API Key Encryption**: Fernet symmetric encryption
- ✅ **Configuration History**: Snapshots and versioning
- ✅ **Dual-Backend**: SQLite primary, YAML fallback
- ✅ **Zero Breaking Changes**: Existing YAML configs still work

## Quick Start

### 1. Migrate Existing YAML to Database

```bash
# Run migration (creates backup automatically)
python3 -m src.oxide.config.migration

# Verify migration
python3 -m src.oxide.config.migration --verify

# See all options
python3 -m src.oxide.config.migration --help
```

### 2. How It Works

After migration:

1. **Config loaded from SQLite** (`~/.oxide/config.db`)
2. **Web UI can modify config** in real-time
3. **YAML still works** as fallback if database is empty

### 3. Migration Output

```
Starting migration from config/default.yaml...
✅ Configuration is valid
✅ Created backup: config/default.yaml.backup.20260108_193943

Migrating services... ✓ gemini ✓ qwen ✓ ollama_local ...
Migrating routing rules... ✓ code_generation ✓ quick_query ...
Migrating execution settings... ✓

✅ Migration completed successfully!

Statistics:
  Services migrated: 6
  Routing rules migrated: 9
  Execution settings: migrated
```

## Database Schema

### Services Table

Stores all LLM service configurations:

```sql
CREATE TABLE services (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,              -- 'cli' or 'http'
    enabled BOOLEAN DEFAULT 1,

    -- CLI specific
    executable TEXT,

    -- HTTP specific
    base_url TEXT,
    api_type TEXT,                   -- 'ollama' or 'openai_compatible'
    api_key_encrypted TEXT,          -- Encrypted with Fernet
    default_model TEXT,

    -- Common fields
    max_context_tokens INTEGER,
    capabilities TEXT,               -- JSON array
    models TEXT,                     -- JSON array

    -- Metadata
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,

    -- Node association (for distributed setup)
    node_id TEXT
);
```

### Routing Rules Table

Stores task routing configuration:

```sql
CREATE TABLE routing_rules (
    task_type TEXT PRIMARY KEY,
    primary_service TEXT NOT NULL,
    fallback_services TEXT,          -- JSON array
    parallel_threshold_files INTEGER,
    timeout_seconds INTEGER,

    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
```

### Execution Settings Table

Singleton table for global execution settings:

```sql
CREATE TABLE execution_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    max_parallel_workers INTEGER DEFAULT 3,
    timeout_seconds INTEGER DEFAULT 120,
    streaming BOOLEAN DEFAULT 1,
    retry_on_failure BOOLEAN DEFAULT 1,
    max_retries INTEGER DEFAULT 2,
    updated_at REAL NOT NULL
);
```

## API Key Encryption

API keys are automatically encrypted using Fernet symmetric encryption:

```python
from cryptography.fernet import Fernet

# Encryption key stored in:
# 1. Environment variable: OXIDE_ENCRYPTION_KEY
# 2. Or auto-generated: ~/.oxide/encryption.key

# Keys are encrypted before storage
# Decrypted on-the-fly when loading config
```

## Migration Commands

### Basic Migration

```bash
# Migrate with defaults (creates backup)
python3 -m src.oxide.config.migration
```

### Verify Migration

```bash
# Compare YAML vs Database
python3 -m src.oxide.config.migration --verify

# Output:
# ✅ Migration verification: PASSED
#    Services: 6
#    Routing rules: 9
```

### Export Database to YAML

```bash
# Export current DB config to YAML
python3 -m src.oxide.config.migration --export backup.yaml

# Useful for:
# - Creating backups
# - Sharing configuration
# - Reverting to YAML-only setup
```

### Migration Without Backup

```bash
# Skip YAML backup (not recommended)
python3 -m src.oxide.config.migration --no-backup
```

## Dual-Backend System

### How Loader Works

```python
def load_config():
    # 1. Try SQLite first
    if db.has_config():
        return db.load_config()  # ← Primary source

    # 2. Fallback to YAML
    else:
        return load_yaml()       # ← Fallback source
```

### When Fallback is Used

- ❌ Database file doesn't exist
- ❌ Database is empty (no services/rules)
- ❌ Database is corrupted
- ⚠️ SQLite import fails

In all cases, YAML configuration still works!

## Rollback to YAML

If you want to revert to YAML-only configuration:

### Option 1: Delete Database

```bash
# Remove database
rm ~/.oxide/config.db

# Oxide will automatically use YAML
```

### Option 2: Export & Delete

```bash
# 1. Export current DB to YAML (optional)
python3 -m src.oxide.config.migration --export config/current.yaml

# 2. Delete database
rm ~/.oxide/config.db

# 3. Use exported YAML or original backup
```

## File Locations

```
~/.oxide/
├── config.db              ← SQLite database
├── encryption.key         ← Fernet encryption key
└── tasks.db              ← Task history (separate)

config/
├── default.yaml           ← Original YAML config
└── default.yaml.backup.*  ← Auto-created backups
```

## Programmatic Usage

### Load Config in Code

```python
from src.oxide.config.loader import load_config

# Automatically uses SQLite or YAML
config = load_config()

print(f"Services: {config.get_enabled_services()}")
```

### Access Database Directly

```python
from src.oxide.utils.config_storage_sqlite import ConfigStorageSQLite

storage = ConfigStorageSQLite()

# Get all services
services = storage.list_services()

# Add new service
storage.add_service('my_service', {
    'type': 'http',
    'base_url': 'http://localhost:8080',
    'enabled': True
})

# Update routing rule
storage.add_routing_rule('custom_task', {
    'primary': 'my_service',
    'fallback': ['qwen', 'ollama_local'],
    'timeout_seconds': 60
})
```

### Migration Programmatically

```python
from src.oxide.config.migration import migrate_config

# Migrate with defaults
result = migrate_config()

if result['status'] == 'success':
    print(f"Migrated {result['services_migrated']} services")
    print(f"Backup: {result['backup_path']}")
```

## Next Steps

Once migration is complete:

1. ✅ Start using Web UI for configuration
2. ✅ Add/remove services via API
3. ✅ Update routing rules dynamically
4. ✅ Configuration changes persist automatically

## Troubleshooting

### "Database is locked"

SQLite is in WAL mode with concurrent access. If you see this error:

```bash
# Check for stale connections
lsof ~/.oxide/config.db

# Restart application
```

### "Encryption key not found"

If encryption key is lost, you can reset:

```bash
# WARNING: This will re-encrypt all API keys
rm ~/.oxide/encryption.key

# Re-migrate from YAML
rm ~/.oxide/config.db
python3 -m src.oxide.config.migration
```

### "Configuration mismatch after migration"

Verify migration:

```bash
python3 -m src.oxide.config.migration --verify
```

If verification fails, check backup and re-migrate:

```bash
# Use specific backup
cp config/default.yaml.backup.TIMESTAMP config/default.yaml

# Re-migrate
rm ~/.oxide/config.db
python3 -m src.oxide.config.migration
```

## Security Notes

- ✅ API keys encrypted at rest (Fernet)
- ✅ Encryption key auto-generated
- ✅ Thread-safe concurrent access
- ✅ ACID transactions

**Best Practices:**
- Backup encryption key: `~/.oxide/encryption.key`
- Set `OXIDE_ENCRYPTION_KEY` env var in production
- Don't commit `.oxide/` directory to git

## Support

For issues or questions:
- GitHub: https://github.com/yayoboy/oxide/issues
- Linear: https://linear.app/yayoboy/project/oxide-llm-orchestrator-616b6601d162
