#!/bin/bash

set -eo pipefail
set -x

pg_isready --quiet || {
 echo "PostgreSQL is not ready" >&2
 exit 1
}

DB_SCHEMA=${DB_SCHEMA:? The DB_SCHEMA environment variable must be set}
DB_NAME=${DB_NAME:? The DB_NAME environment variable must be set}

ADMIN_TOKEN=${ADMIN_TOKEN:="00000000000000000000000000000000"}

sudo -u postgres psql -d ${DB_NAME} << EOF
INSERT INTO ${DB_SCHEMA}."token" (token, description, date_issued) VALUES ('${ADMIN_TOKEN}', 'Admin token', NOW());
EOF
