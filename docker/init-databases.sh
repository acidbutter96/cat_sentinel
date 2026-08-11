#!/usr/bin/env bash
set -euo pipefail

# Runs once, on first container init, via docker-entrypoint-initdb.d.
# The postgres image only creates POSTGRES_DB by default; this service
# needs two separate databases (one per backend that owns its own schema).
for db in cat_sentinel camera; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE $db OWNER $POSTGRES_USER'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '$db')\gexec
EOSQL
done
