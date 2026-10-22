#!/bin/bash

set -eo pipefail

PORT=${PORT:? The PORT environment variable must be set}
APP_ENV=${APP_ENV:-prod}

source /app/bin/activate

uvicorn_args=(--host 0.0.0.0 --port "$PORT" --log-config /app/docker/logging.json)

case "$APP_ENV" in
  dev)  uvicorn_args+=(--app-dir /app/src --reload --reload-dir /app/src) ;;
  prod) ;;
  *)    echo "APP_ENV must be 'dev' or 'prod', got '$APP_ENV'" >&2; exit 1 ;;
esac

ENABLE_TLS=$(tr '[:upper:]' '[:lower:]' <<< "${ENABLE_TLS:-}")

case "$ENABLE_TLS" in
  y|yes|true|1)
    SSL_KEYFILE=${SSL_KEYFILE:-/certs/tls.key}
    SSL_CERTFILE=${SSL_CERTFILE:-/certs/tls.crt}
    for f in "$SSL_KEYFILE" "$SSL_CERTFILE"; do
      [[ -r "$f" ]] || { echo "ENABLE_TLS is set but '$f' is not readable" >&2; exit 1; }
    done
    uvicorn_args+=(--ssl-keyfile "$SSL_KEYFILE" --ssl-certfile "$SSL_CERTFILE")
    ;;
esac

exec uvicorn npg_porch.server:app "${uvicorn_args[@]}" "$@"
