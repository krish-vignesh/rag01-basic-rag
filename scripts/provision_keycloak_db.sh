
#!/usr/bin/env bash
set -Eeuo pipefail

: "${PGHOST:?Missing PostgreSQL host}"
: "${PGPORT:?Missing PostgreSQL port}"
: "${PGUSER:?Missing PostgreSQL administrator username}"
: "${PGPASSWORD:?Missing PostgreSQL administrator password}"
: "${KEYCLOAK_DB:?Missing Keycloak database name}"
: "${KEYCLOAK_DB_USER:?Missing Keycloak database username}"
: "${KEYCLOAK_DB_PASSWORD:?Missing Keycloak database password}"

echo "Waiting for PostgreSQL..."

until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER"; do
    sleep 2
done

echo "Checking Keycloak database role..."

psql -v ON_ERROR_STOP=1 -d postgres \
    -v role="$KEYCLOAK_DB_USER" \
    -v role_password="$KEYCLOAK_DB_PASSWORD" <<'SQL'
SELECT format(
    'CREATE ROLE %I LOGIN PASSWORD %L',
    :'role',
    :'role_password'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_roles WHERE rolname = :'role'
)
\gexec
SQL

echo "Checking Keycloak database..."

psql -v ON_ERROR_STOP=1 -d postgres \
    -v database="$KEYCLOAK_DB" \
    -v role="$KEYCLOAK_DB_USER" <<'SQL'
SELECT format(
    'CREATE DATABASE %I OWNER %I',
    :'database',
    :'role'
)
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = :'database'
)
\gexec
SQL


echo "Validating database ownership..."

if [[ ! "$KEYCLOAK_DB" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
    echo "ERROR: Invalid database name."
    exit 1
fi

OWNER=$(
    psql -X -v ON_ERROR_STOP=1 -d postgres -Atc \
        "SELECT pg_get_userbyid(datdba)
         FROM pg_database
         WHERE datname = '$KEYCLOAK_DB';"
)

if [[ "$OWNER" != "$KEYCLOAK_DB_USER" ]]; then
    echo "ERROR: Database owner is '$OWNER', expected '$KEYCLOAK_DB_USER'."
    exit 1
fi

echo "Keycloak database provisioning verified successfully."

