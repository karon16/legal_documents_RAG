# Database Migrations

This directory is intended for future database migrations.
Currently, the database is initialized automatically via the `db/init/` scripts when the `postgres` Docker container starts for the first time.

When deploying updates to the schema after initial deployment, you should:
1. Create a migration script here, e.g., `V1_1__add_new_column.sql`.
2. Apply it using a migration tool (e.g., Flyway, Liquibase, or manually via `psql`).
3. Update the base `init/` scripts to reflect the final schema state for fresh deployments.

**Important**: Ensure all migration scripts are idempotent (`IF NOT EXISTS`) to allow safe re-execution if necessary.
