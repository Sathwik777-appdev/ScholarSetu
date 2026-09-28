#!/bin/bash
# VM boot script: install Docker (first boot), write secrets from Secret Manager, start the backend.
set -euo pipefail
META=http://metadata.google.internal/computeMetadata/v1/instance/attributes
attr() { curl -sf -H "Metadata-Flavor: Google" "$META/$1"; }
ENV_NAME=$(attr scholarsetu-env); REPO=$(attr scholarsetu-repo); TAG=$(attr scholarsetu-tag)
CLOUDSQL_INSTANCE=$(attr scholarsetu-cloudsql); DEMO_MODE=$(attr scholarsetu-demo-mode)

if ! command -v docker >/dev/null; then
  apt-get update && apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian $(. /etc/os-release; echo $VERSION_CODENAME) stable" > /etc/apt/sources.list.d/docker.list
  apt-get update && apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
fi
gcloud auth configure-docker asia-south1-docker.pkg.dev --quiet

mkdir -p /opt/scholarsetu && cd /opt/scholarsetu
secret() { gcloud secrets versions access latest --secret "scholarsetu-${ENV_NAME}-$1"; }
umask 077
cat > .env <<ENV
JWT_SECRET=$(secret jwt-secret)
PPRL_HMAC_KEY=$(secret pprl-key)
SMS_GATEWAY_TOKEN=$(secret sms-token)
DEMO_MODE=${DEMO_MODE}
SLA_DEMO_SECONDS=3600
LOG_LEVEL=INFO
DIGILOCKER_CLIENT_ID=scholarsetu-${ENV_NAME}
DIGILOCKER_CLIENT_SECRET=$(secret digilocker-client-secret || true)
ENV
cat > compose.env <<ENV
REPO=${REPO}
TAG=${TAG}
CLOUDSQL_INSTANCE=${CLOUDSQL_INSTANCE}
DATABASE_URL_VM=$(secret database-url-vm)
ENV
attr scholarsetu-compose > docker-compose.yml
docker compose --env-file compose.env pull
docker compose --env-file compose.env up -d --remove-orphans
