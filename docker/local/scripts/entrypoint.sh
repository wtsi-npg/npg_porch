#!/bin/bash

set -eo pipefail

sudo service postgresql start

pg_isready --quiet --timeout=30 || {
 echo "PostgreSQL is not ready" >&2
 exit 1
}

PORT=${PORT:? The PORT environment variable must be set}

source /app/bin/activate

exec uvicorn npg_porch.server:app --host 0.0.0.0 --port ${PORT} --reload --log-config /app/docker/logging.json
