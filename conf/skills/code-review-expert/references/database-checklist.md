# Database & Flyway Migration Checklist

## [P0] Schema Compatibility — Released Scripts Are Immutable

This is the single most dangerous Flyway mistake: modifying a script that has already run in any environment.

- Flyway checksums each script on first execution; any change causes `FlywayValidateException` and the service **cannot start**
- The only exception: a script with a severe bug that must be fixed, and even then coordinate with all environments
- If you need to change schema that was already migrated, create a **new** migration script
- Scripts that have been executed in ANY environment must never be renamed, split, or merged — this causes history table mismatch
- Unreleased scripts (not yet run in any environment) MAY be consolidated into fewer files for a cleaner baseline

## [P0] Large Table DDL Strategy

When a single table exceeds **5 million rows** or **2GB**, direct DDL operations risk long-duration table locks that block all business queries.

### Adding Columns (MySQL 8.0+)
- Verify the ALTER TABLE supports `ALGORITHM=INSTANT` (metadata-only change, millisecond-level)
- INSTANT only works for **appending columns at the end** — do NOT use `AFTER column_name`, which may degrade to COPY algorithm
- INSTANT does not work on compressed tables

### Other DDL on Large Tables
- Create a new table with the desired schema
- Migrate data in batches
- Rename old table → backup, new table → original name
- This avoids any prolonged lock on the production table

### Questions to Ask
- "How many rows does this table have in production?"
- "Will this ALTER TABLE acquire a metadata lock or copy the entire table?"
- "Is there a rollback plan if the migration fails midway?"

---

## [P0] SQL Idempotency — Version Scripts Are NOT an Excuse for Non-Idempotent SQL

Flyway's version management only guarantees the framework executes a script once. It does NOT replace the requirement that the SQL itself should be safe if manually re-executed. Design every migration as "safe to run repeatedly by hand."

### DDL: Use Existence-Check Patterns
- Prefer `CREATE TABLE IF NOT EXISTS` over bare `CREATE TABLE`
- Use project utilities like `proc_add_column`, `proc_modify_column`, `proc_add_column_index` that include existence checks internally
- Before using bare `ALTER TABLE` or `DROP`, confirm whether the project already has idempotent wrapper procedures

### DML: Backfill/Seed Must Have Guard Conditions
- `UPDATE` must limit scope to un-migrated rows (e.g., `WHERE new_column IS NULL`)
- `INSERT` must use `INSERT IGNORE`, `WHERE NOT EXISTS`, or equivalent protection — avoid duplicate inserts, overwrites, or double-counting
- Never write open-ended `UPDATE ... SET x = y` without a condition that makes it safe on re-run

### Destructive Operations Require Explicit Justification
- `DROP TABLE`, `DROP COLUMN`, irreversible data corrections, and any migration that relies on "execute exactly once" semantics must include a SQL comment explaining:
  - Why the operation is necessary
  - Preconditions (what state must be true before running)
  - Risk if re-executed
  - How to verify success
- If the operation CAN be rewritten as idempotent, do so. "It's a one-time script" is not an acceptable default.

### Questions to Ask
- "If this script runs twice by accident, what breaks?"
- "Does this UPDATE have a WHERE clause that prevents double-application?"
- "Is there a project utility for this DDL operation that handles existence checks?"

---

## [P2] Script Naming Convention

- File name must follow version format: `V{major}.{minor}.{patch}_{seq}__{description}.sql`
  - Example: `V1.1.0_1__order_create_main_table.sql`
- Version numbers must strictly increment — gaps or duplicates break Flyway ordering
- Each developer should have a unique identifier/sequence range to avoid conflicts
- New scripts must target the lowest required version; adding to a higher version and then backporting causes upgrade failures

## [P2] DDL Standards

### Audit Fields
Every new table must include standard audit columns:
- `create_time` — record creation timestamp
- `update_time` — last modification timestamp
- Additional as needed: `create_by`, `update_by`, `is_deleted`

### Column Naming
- Use `snake_case` for column names
- Boolean columns: prefix with `is_` (e.g., `is_deleted`, `is_active`)

## [P2] Migration Type Restrictions

### JavaMigration
- Avoid JavaMigration (`V__*.java`) for startup-time execution
- Complex data cleaning or transformation must be done via independent task scripts, not during service bootstrap
- JavaMigration during startup adds latency and can cause timeout-related failures in container orchestration

