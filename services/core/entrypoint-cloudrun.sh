#!/bin/bash
set -e

# Ensure PostgreSQL run directory exists with proper permissions
mkdir -p /var/run/postgresql /var/lib/postgresql/data
chown -R postgres:postgres /var/run/postgresql /var/lib/postgresql

echo "Starting local PostgreSQL server..."
su - postgres -c "/usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/data -l /var/lib/postgresql/data/logfile start -w"

# Ensure secrets directory exists for demo attestation key
mkdir -p "$(dirname "${ATTESTATION_PRIVATE_KEY_PATH:-/app/secrets/attestation_ed25519.pem}")"

PORT_NUM="${PORT:-8080}"
echo "ScholarSetu Core API listening on port $PORT_NUM..."
exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT_NUM" --proxy-headers
