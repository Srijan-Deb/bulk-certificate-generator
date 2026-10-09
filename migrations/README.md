# Database Migrations

The Bulk Certificate Generator uses **Alembic** for schema migrations.

Migration scripts and configuration live in [`../alembic/`](../alembic/):
- **`alembic/env.py`**: Configures database engine connection and binds SQLAlchemy models.
- **`alembic/versions/`**: Contains version-controlled revision files (e.g., `dfb1ace84fda_initial_schema.py`).
- **`alembic.ini`**: Root Alembic configuration file.

## Common Migration Commands

```bash
# Apply all pending migrations to database
alembic upgrade head

# Generate a new migration revision based on SQLAlchemy model changes
alembic revision --autogenerate -m "describe_changes"

# Roll back the most recent migration
alembic downgrade -1

# Show current migration revision
alembic current
```
