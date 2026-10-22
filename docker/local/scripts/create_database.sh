#!/bin/bash

set -eo pipefail
set -x

pg_isready --quiet || {
 echo "PostgreSQL is not ready" >&2
 exit 1
}

DB_SCHEMA=${DB_SCHEMA:? The DB_SCHEMA environment variable must be set}
DB_NAME=${DB_NAME:? The DB_NAME environment variable must be set}
DB_USER=${DB_USER:? The DB_USER environment variable must be set}
DB_PASS=${DB_PASS:? The DB_PASS environment variable must be set}

sudo -u postgres createuser -D -R -S ${DB_USER}
sudo -u postgres createdb -O ${DB_USER} ${DB_NAME}

sudo -u postgres psql -d ${DB_NAME} << EOF
ALTER USER ${DB_USER} WITH PASSWORD '${DB_PASS}';

CREATE SCHEMA ${DB_SCHEMA};

SET search_path TO ${DB_SCHEMA}, public;

GRANT ALL PRIVILEGES ON SCHEMA ${DB_SCHEMA} TO ${DB_USER};
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ${DB_SCHEMA} TO ${DB_USER};
GRANT USAGE ON ALL SEQUENCES IN SCHEMA ${DB_SCHEMA} TO ${DB_USER};
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA ${DB_SCHEMA} TO ${DB_USER};
EOF
