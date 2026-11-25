#!/usr/bin/env bash
set -Eeuo pipefail

: "${PGHOST:?Missing PostgreSQL host}"
: "${PGPORT:?Missing PostgreSQL port}"
: "${PGUSER:?Missing PostgreSQL administrator username}"
: "${PGPASSWORD:?Missing PostgreSQL administrator password}"
: "${POSTGRES_TEST_DB:?Missing test database name}"
: "${POSTGRES_TEST_USER:?Missing test database username}"
: "${POSTGRES_TEST_PASSWORD:?Missing test database password}"

if [[ ! "$POSTGRES_TEST_DB" =~ ^[a-z_][a-z0-9_]*$ ]]; then
    echo "ERROR: Invalid test database name." >&2
    exit 1
fi

if [[ ! "$POSTGRES_TEST_USER" =~ ^[a-z_][a-z0-9_]*$ ]]; then
    echo "ERROR: Invalid test database username." >&2
    exit 1
fi

psql_admin() {
    psql -X -v ON_ERROR_STOP=1 "$@"
}

echo "Waiting for PostgreSQL..."
until pg_isready -h "$PGHOST" -p "$PGPORT" -U "$PGUSER" >/dev/null 2>&1; do
    sleep 2
done

database_state="$(
    psql_admin \
        -d postgres \
        -At \
        -F '|' \
        -c "SELECT pg_get_userbyid(datdba),
                    has_database_privilege('public', datname, 'CONNECT')
             FROM pg_database
             WHERE datname = '$POSTGRES_TEST_DB';"
)"

if [[ -n "$database_state" ]]; then
    expected_database_state="${POSTGRES_TEST_USER}|f"
    if [[ "$database_state" != "$expected_database_state" ]]; then
        echo "ERROR: Existing test database has unexpected owner or ACLs." >&2
        exit 1
    fi

    database_exists="true"
else
    database_exists="false"
fi

role_state="$(
    psql_admin \
        -d postgres \
        -At \
        -F '|' \
        -c "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                    rolreplication, rolbypassrls
             FROM pg_roles
             WHERE rolname = '$POSTGRES_TEST_USER';"
)"

if [[ -n "$role_state" ]]; then
    if [[ "$role_state" != "t|f|f|f|f|f" ]]; then
        echo "ERROR: Existing test role has unexpected attributes." >&2
        exit 1
    fi

    role_created="false"
else
    if [[ "$database_exists" == "true" ]]; then
        echo "ERROR: Test database owner exists but its role is missing." >&2
        exit 1
    fi

    psql_admin \
        -d postgres \
        -c "CREATE ROLE \"$POSTGRES_TEST_USER\"
            NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
            NOINHERIT NOREPLICATION NOBYPASSRLS"

    printf '%s\n%s\n' "$POSTGRES_TEST_PASSWORD" "$POSTGRES_TEST_PASSWORD" |
        psql_admin \
            -d postgres \
            -c "\password $POSTGRES_TEST_USER"

    psql_admin \
        -d postgres \
        -c "ALTER ROLE \"$POSTGRES_TEST_USER\" LOGIN"

    role_created="true"
fi

if [[ "$database_exists" == "true" ]]; then
    database_created="false"
else
    psql_admin \
        -d postgres \
        -c "CREATE DATABASE \"$POSTGRES_TEST_DB\"
            OWNER \"$POSTGRES_TEST_USER\""

    psql_admin \
        -d postgres \
        -c "REVOKE CONNECT ON DATABASE \"$POSTGRES_TEST_DB\" FROM PUBLIC;
            GRANT CONNECT ON DATABASE \"$POSTGRES_TEST_DB\"
                TO \"$POSTGRES_TEST_USER\";
            GRANT CONNECT ON DATABASE \"$POSTGRES_TEST_DB\"
                TO CURRENT_USER;"

    psql_admin \
        -d "$POSTGRES_TEST_DB" \
        -c "REVOKE CREATE ON SCHEMA public FROM PUBLIC;
            GRANT USAGE, CREATE ON SCHEMA public
                TO \"$POSTGRES_TEST_USER\";"

    database_created="true"
fi

if [[ "$role_created" == "true" ]]; then
    test_role_state="$(
        psql_admin \
            -d postgres \
            -At \
            -F '|' \
            -c "SELECT rolcanlogin, rolsuper, rolcreatedb, rolcreaterole,
                        rolreplication, rolbypassrls
                 FROM pg_roles
                 WHERE rolname = '$POSTGRES_TEST_USER';"
    )"

    if [[ "$test_role_state" != "t|f|f|f|f|f" ]]; then
        echo "ERROR: Newly created test role has unexpected attributes." >&2
        exit 1
    fi
fi

if [[ "$database_created" == "true" ]]; then
    database_acl_state="$(
        psql_admin \
            -d postgres \
            -At \
            -F '|' \
            -c "SELECT pg_get_userbyid(datdba),
                        has_database_privilege(
                            'public', datname, 'CONNECT'
                        ),
                        has_database_privilege(
                            '$POSTGRES_TEST_USER', datname, 'CONNECT'
                        )
                 FROM pg_database
                 WHERE datname = '$POSTGRES_TEST_DB';"
    )"

    if [[ "$database_acl_state" != "${POSTGRES_TEST_USER}|f|t" ]]; then
        echo "ERROR: New test database ACL verification failed." >&2
        exit 1
    fi
fi

PGPASSWORD="$POSTGRES_TEST_PASSWORD" \
    psql \
        -X \
        -v ON_ERROR_STOP=1 \
        -h "$PGHOST" \
        -p "$PGPORT" \
        -U "$POSTGRES_TEST_USER" \
        -d "$POSTGRES_TEST_DB" \
        -At \
        -c 'SELECT current_database();' >/dev/null

echo "Test database and role provisioning verified successfully."
