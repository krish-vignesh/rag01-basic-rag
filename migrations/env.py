import asyncio
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import URL, pool, text
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from src.config.migration_settings import MigrationSettings
from src.models.orm import Base

# --------------------------------------------------
# 1. Alembic configuration
# --------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# --------------------------------------------------
# 2. ORM metadata registration
# --------------------------------------------------

target_metadata = Base.metadata


# --------------------------------------------------
# 3. Migration settings
# --------------------------------------------------

migration_settings = MigrationSettings()


# --------------------------------------------------
# 4. Migration target selection
# --------------------------------------------------


def get_migration_target() -> str:
    """Return the explicitly selected migration database target."""

    return migration_settings.migration_target


# --------------------------------------------------
# 5. Development database safeguard
# --------------------------------------------------


def validate_migration_target(target: str) -> None:
    """Prevent development operations without explicit approval."""

    if target not in {"test", "development"}:
        raise RuntimeError("Unsupported migration target.")

    if target == "development" and not migration_settings.allow_development_migrations:
        raise RuntimeError(
            "Development migrations are disabled. "
            "Set RAG01_ALLOW_DEVELOPMENT_MIGRATIONS=true "
            "only when deliberately operating on development."
        )


# --------------------------------------------------
# 6. Database URL construction and validation
# --------------------------------------------------


def get_database_url(target: str) -> URL:
    """Build and validate the URL for the selected database."""

    if target == "test":
        database_name = migration_settings.postgres_test_db
        username = migration_settings.postgres_test_user
        password = migration_settings.postgres_test_password

        expected_database = "rag01_test"

    elif target == "development":
        database_name = migration_settings.postgres_db
        username = migration_settings.postgres_user
        password = migration_settings.postgres_password

        expected_database = "rag01_metadata"

    else:
        raise RuntimeError("Unsupported migration target.")

    required_values = {
        "database name": database_name,
        "username": username,
        "password": password,
        "host": migration_settings.postgres_host,
    }

    missing_values = [
        name
        for name, value in required_values.items()
        if value is None or not value.strip()
    ]

    if missing_values:
        raise RuntimeError(
            "Missing required database configuration: " + ", ".join(missing_values)
        )

    if database_name != expected_database:
        raise RuntimeError(
            f"Database target mismatch: '{target}' must use '{expected_database}'."
        )

    return URL.create(
        drivername="postgresql+psycopg",
        username=username,
        password=password,
        host=migration_settings.postgres_host,
        port=migration_settings.postgres_port,
        database=database_name,
    )


# --------------------------------------------------
# 7. Schema and table filtering
# --------------------------------------------------


def include_name(name, type_, parent_names) -> bool:
    """Restrict Alembic inspection to our public application schema."""

    if type_ == "schema":
        # PostgreSQL's default schema may be represented as None.
        return name in (None, "public")

    if type_ == "table":
        managed_tables = {table.name for table in target_metadata.tables.values()}

        schema_name = parent_names.get("schema_name")

        return schema_name in (None, "public") and name in managed_tables

    return True


# --------------------------------------------------
# 8. Database identity validation
# --------------------------------------------------


def validate_database_identity(
    connection: Connection,
    target: str,
) -> None:
    """Ensure the connection reached the intended database and user."""

    if target == "test":
        expected_database = "rag01_test"
        expected_user = migration_settings.postgres_test_user

    elif target == "development":
        expected_database = "rag01_metadata"
        expected_user = migration_settings.postgres_user

    else:
        raise RuntimeError("Unsupported migration target.")

    result = connection.execute(
        text("""
            SELECT
                current_database(),
                current_user,
                inet_server_addr(),
                inet_server_port()
        """)
    ).one()

    actual_database, actual_user, server_address, server_port = result

    print(
        f"Alembic connected to: "
        f"{actual_database} as {actual_user} "
        f"at {server_address}:{server_port}"
    )

    if actual_database != expected_database:
        raise RuntimeError("Migration aborted: connected to an unexpected database.")

    if actual_user != expected_user:
        raise RuntimeError(
            "Migration aborted: connected using an unexpected database user."
        )


# --------------------------------------------------
# 9. Migration execution
# --------------------------------------------------


def do_run_migrations(connection: Connection) -> None:
    """Configure and execute migrations using the supplied connection."""

    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=include_name,
        version_table_schema="public",
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# --------------------------------------------------
# 10. Async migration engine
# --------------------------------------------------


async def run_async_migrations() -> None:
    """Create and dispose a dedicated async migration engine."""

    target = get_migration_target()

    validate_migration_target(target)

    database_url = get_database_url(target)

    connectable = create_async_engine(
        database_url,
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            # Verify the database identity first.
            await connection.run_sync(
                validate_database_identity,
                target,
            )

            # End the transaction started by the identity SELECT.
            await connection.commit()

            # Run migrations in their own transaction.
            await connection.run_sync(do_run_migrations)

    finally:
        await connectable.dispose()


# --------------------------------------------------
# 11. Alembic online entry point
# --------------------------------------------------


def run_migrations_online() -> None:
    """Run migrations using the explicitly selected database."""

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(run_async_migrations())


# --------------------------------------------------
# 12. Entry point
# --------------------------------------------------

if context.is_offline_mode():
    raise RuntimeError("Offline migrations are not supported by this project.")

run_migrations_online()
