#!/usr/bin/env bash
# ScholarSetu on Google Cloud, one environment at a time (demo or prod).
#
#   ENV=demo deploy/gcp/deploy.sh all        # everything, in order
#   ENV=demo deploy/gcp/deploy.sh <step>     # one step: apis sql bucket secrets images vm migrate api monitor
#
# Layout per environment:
#   Cloud Run  scholarsetu-api (demo) / scholarsetu-api-prod   request-driven API, scales to zero
#   Cloud SQL  scholarsetu-db (shared instance), database scholarsetu_<env>, daily backups
#   GCS        <project>-scholarsetu-<env>-wallet               wallet documents (S3 API, HMAC key)
#   VM         scholarsetu-backend-<env> (e2-small)             NATS, Temporal, worker, mocks, SQL proxy
#   Secrets    scholarsetu-<env>-*                              generated here, never printed or stored locally
#
# Steps are idempotent: re-running one keeps what exists (secrets are never regenerated once created).
set -euo pipefail

ENV=${ENV:?set ENV=demo or ENV=prod}
PROJECT=${PROJECT:-trisphere-4b121}
REGION=${REGION:-asia-south1}
ZONE=${ZONE:-asia-south1-a}
REPO=$REGION-docker.pkg.dev/$PROJECT/cloud-run-source-deploy
TAG=${TAG:-$(git rev-parse --short HEAD)}
SQL_INSTANCE=scholarsetu-db
DB=scholarsetu_$ENV
DB_USER=scholarsetu_$ENV
BUCKET=$PROJECT-scholarsetu-$ENV-wallet
SA=scholarsetu-$ENV
SA_EMAIL=$SA@$PROJECT.iam.gserviceaccount.com
VM=scholarsetu-backend-$ENV
SERVICE=$([ "$ENV" = demo ] && echo scholarsetu-api || echo scholarsetu-api-$ENV)
DEMO_MODE=$([ "$ENV" = demo ] && echo true || echo false)
CONNECTION=$PROJECT:$REGION:$SQL_INSTANCE
ALERT_EMAIL=${ALERT_EMAIL:-$(gcloud config get-value account 2>/dev/null)}

g() { gcloud --project "$PROJECT" "$@"; }
exists() { "$@" >/dev/null 2>&1; }
rand() { openssl rand -hex "$1"; }
put_secret() {  # put_secret NAME VALUE  (creates once; never overwrites)
  local name=scholarsetu-$ENV-$1
  if exists g secrets describe "$name"; then echo "  secret $name exists (kept)"; return; fi
  printf '%s' "$2" | g secrets create "$name" --replication-policy=automatic --data-file=- >/dev/null
  echo "  secret $name created"
}

apis() {
  g services enable sqladmin.googleapis.com secretmanager.googleapis.com compute.googleapis.com \
    run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com monitoring.googleapis.com
}

sql() {
  if ! exists g sql instances describe "$SQL_INSTANCE"; then
    g sql instances create "$SQL_INSTANCE" --database-version=POSTGRES_16 --edition=ENTERPRISE \
      --tier=db-f1-micro --region="$REGION" --storage-size=10 --storage-auto-increase \
      --backup-start-time=20:30 --retained-backups-count=7 --enable-point-in-time-recovery
  fi
  exists g sql databases describe "$DB" --instance "$SQL_INSTANCE" || g sql databases create "$DB" --instance "$SQL_INSTANCE"
  if ! exists g secrets describe "scholarsetu-$ENV-database-url"; then
    local pw; pw=$(rand 24)
    if exists g sql users describe "$DB_USER" --instance "$SQL_INSTANCE"; then
      g sql users set-password "$DB_USER" --instance "$SQL_INSTANCE" --password "$pw" >/dev/null
    else
      g sql users create "$DB_USER" --instance "$SQL_INSTANCE" --password "$pw" >/dev/null
    fi
    # Cloud Run connects through the built-in connector (unix socket); the VM through the Cloud SQL proxy.
    put_secret database-url "postgresql+asyncpg://$DB_USER:$pw@/$DB?host=/cloudsql/$CONNECTION"
    put_secret database-url-vm "postgresql+asyncpg://$DB_USER:$pw@cloudsql:5432/$DB"
  fi
}

bucket() {
  exists g iam service-accounts describe "$SA_EMAIL" || \
    g iam service-accounts create "$SA" --display-name "ScholarSetu $ENV (API, worker)"
  exists gcloud storage buckets describe "gs://$BUCKET" || \
    gcloud storage buckets create "gs://$BUCKET" --project "$PROJECT" --location "$REGION" \
      --uniform-bucket-level-access --public-access-prevention
  # objectAdmin for the documents; legacyBucketReader because the S3 API checks the bucket first.
  for role in roles/storage.objectAdmin roles/storage.legacyBucketReader; do
    gcloud storage buckets add-iam-policy-binding "gs://$BUCKET" --member "serviceAccount:$SA_EMAIL" \
      --role "$role" >/dev/null
  done
  for role in roles/cloudsql.client roles/secretmanager.secretAccessor roles/artifactregistry.reader \
              roles/logging.logWriter roles/monitoring.metricWriter; do
    g projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA_EMAIL" --role "$role" \
      --condition=None >/dev/null
  done
  if ! exists g secrets describe "scholarsetu-$ENV-hmac-access"; then
    local out; out=$(gcloud storage hmac create "$SA_EMAIL" --project "$PROJECT" --format='value(metadata.accessId,secret)')
    put_secret hmac-access "$(echo "$out" | cut -f1)"
    put_secret hmac-secret "$(echo "$out" | cut -f2)"
  fi
}

secrets() {
  put_secret jwt-secret "$(rand 32)"
  put_secret pprl-key "$(rand 32)"
  put_secret sms-token "$(rand 24)"
  put_secret skill-token "$(rand 24)"
  if ! exists g secrets describe "scholarsetu-$ENV-attestation-key"; then
    local key; key=$(mktemp); openssl genpkey -algorithm ed25519 -out "$key" 2>/dev/null
    g secrets create "scholarsetu-$ENV-attestation-key" --replication-policy=automatic --data-file="$key" >/dev/null
    rm -f "$key"; echo "  secret scholarsetu-$ENV-attestation-key created"
  fi
  # Optional: GEMINI_API_KEY. Copy it in with: printf %s "$KEY" | gcloud secrets create scholarsetu-$ENV-gemini-key --data-file=-
}

images() {
  g builds submit --config deploy/gcp/cloudbuild.yaml --substitutions "_TAG=$TAG" .
}

vm() {
  # The VM has no public IP: it reaches Google APIs, Docker Hub and GitHub through Cloud NAT, which must
  # exist before it boots.
  g compute routers describe scholarsetu-router --region "$REGION" >/dev/null 2>&1 || \
    g compute routers create scholarsetu-router --network default --region "$REGION"
  g compute routers nats describe scholarsetu-nat --router scholarsetu-router --region "$REGION" >/dev/null 2>&1 || \
    g compute routers nats create scholarsetu-nat --router scholarsetu-router --region "$REGION" \
      --auto-allocate-nat-external-ips --nat-all-subnet-ip-ranges
  g compute firewall-rules describe scholarsetu-mocks-from-run >/dev/null 2>&1 || \
    g compute firewall-rules create scholarsetu-mocks-from-run --network default --direction INGRESS \
      --allow tcp:8100 --source-ranges "$(g compute networks subnets describe default --region "$REGION" --format='value(ipCidrRange)')" \
      --target-tags scholarsetu-backend
  local meta="scholarsetu-env=$ENV,scholarsetu-repo=$REPO,scholarsetu-tag=$TAG,scholarsetu-cloudsql=$CONNECTION,scholarsetu-demo-mode=$DEMO_MODE"
  local files="startup-script=deploy/gcp/vm/startup.sh,scholarsetu-compose=deploy/gcp/vm/docker-compose.yml"
  if exists g compute instances describe "$VM" --zone "$ZONE"; then
    g compute instances add-metadata "$VM" --zone "$ZONE" --metadata "$meta" --metadata-from-file "$files"
    g compute instances reset "$VM" --zone "$ZONE"  # the startup script re-runs on boot with the new image tag
  else
    g compute instances create "$VM" --zone "$ZONE" --machine-type e2-small \
      --image-family debian-12 --image-project debian-cloud --boot-disk-size 20GB \
      --service-account "$SA_EMAIL" --scopes cloud-platform --tags scholarsetu-backend --no-address \
      --shielded-secure-boot --metadata "$meta" --metadata-from-file "$files"
  fi
}

vm_ip() { g compute instances describe "$VM" --zone "$ZONE" --format='value(networkInterfaces[0].networkIP)'; }

run_flags() {  # shared by the API service and the migration job
  local secrets="DATABASE_URL=scholarsetu-$ENV-database-url:latest,JWT_SECRET=scholarsetu-$ENV-jwt-secret:latest"
  secrets+=",PPRL_HMAC_KEY=scholarsetu-$ENV-pprl-key:latest,SMS_GATEWAY_TOKEN=scholarsetu-$ENV-sms-token:latest"
  secrets+=",SKILL_SERVICE_TOKEN=scholarsetu-$ENV-skill-token:latest"
  secrets+=",MINIO_ACCESS_KEY=scholarsetu-$ENV-hmac-access:latest,MINIO_SECRET_KEY=scholarsetu-$ENV-hmac-secret:latest"
  exists g secrets describe "scholarsetu-$ENV-gemini-key" && secrets+=",GEMINI_API_KEY=scholarsetu-$ENV-gemini-key:latest"
  secrets+=",/secrets/attestation/key.pem=scholarsetu-$ENV-attestation-key:latest"
  echo --image "$REPO/scholarsetu-core:$TAG" --region "$REGION" --service-account "$SA_EMAIL" \
    --set-cloudsql-instances "$CONNECTION" --network default --subnet default --vpc-egress private-ranges-only \
    --set-secrets "$secrets" \
    --set-env-vars "DEMO_MODE=$DEMO_MODE,RUN_MIGRATIONS=false,OUTBOX_PUBLISHER_ENABLED=false,ADAPTER_SYNC_INTERVAL_SECONDS=0,MOCK_SERVICE_URL=http://$(vm_ip):8100,MINIO_URL=https://storage.googleapis.com,MINIO_BUCKET=$BUCKET,ATTESTATION_PRIVATE_KEY_PATH=/secrets/attestation/key.pem,SLA_DEMO_SECONDS=3600,DATABASE_POOL_SIZE=3,DATABASE_MAX_OVERFLOW=2,GEMINI_MODEL=${GEMINI_MODEL:-gemini-2.5-flash}" \
    --cpu 1 --memory 2Gi
}

migrate() {
  local job=scholarsetu-migrate-$ENV cmd="alembic upgrade head"
  [ "$ENV" = demo ] && cmd="alembic upgrade head && python /scripts/seed_demo.py"
  # shellcheck disable=SC2046
  g run jobs deploy "$job" $(run_flags) --command sh --args=-c,"$cmd" --max-retries 0 --task-timeout 900
  g run jobs execute "$job" --region "$REGION" --wait
}

api() {
  # shellcheck disable=SC2046
  g run deploy "$SERVICE" $(run_flags) --allow-unauthenticated --min-instances 0 --max-instances 3 \
    --cpu-boost --concurrency 40 --timeout 60
}

monitor() {
  local url host channel
  url=$(g run services describe "$SERVICE" --region "$REGION" --format='value(status.url)'); host=${url#https://}
  if ! g monitoring uptime list-configs --format='value(displayName)' 2>/dev/null | grep -qx "$SERVICE ready"; then
    g monitoring uptime create "$SERVICE ready" --resource-type=uptime-url --resource-labels="host=$host,project_id=$PROJECT" \
      --path=/health/ready --port=443 --protocol=https --period=5 --timeout=30
  fi
  # Alerting through the Monitoring REST API (no gcloud alpha/beta components needed).
  local token api; token=$(gcloud auth print-access-token); api=https://monitoring.googleapis.com/v3/projects/$PROJECT
  channel=$(curl -sf -H "Authorization: Bearer $token" "$api/notificationChannels" | python3 -c "
import json,sys
for c in json.load(sys.stdin).get('notificationChannels', []):
    if c.get('labels', {}).get('email_address') == '$ALERT_EMAIL': print(c['name']); break")
  [ -n "$channel" ] || channel=$(curl -sf -X POST -H "Authorization: Bearer $token" -H 'Content-Type: application/json' \
    "$api/notificationChannels" -d "{\"type\":\"email\",\"displayName\":\"ScholarSetu alerts\",\"labels\":{\"email_address\":\"$ALERT_EMAIL\"}}" \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['name'])")
  if ! curl -sf -H "Authorization: Bearer $token" "$api/alertPolicies" | grep -q "\"$SERVICE down\""; then
    curl -sf -X POST -H "Authorization: Bearer $token" -H 'Content-Type: application/json' "$api/alertPolicies" -d @- >/dev/null <<JSON
{"displayName": "$SERVICE down", "combiner": "OR",
 "conditions": [{"displayName": "Uptime check failing",
   "conditionThreshold": {"filter": "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND resource.label.host=\"$host\"",
     "comparison": "COMPARISON_GT", "thresholdValue": 1, "duration": "300s",
     "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_NEXT_OLDER",
                       "crossSeriesReducer": "REDUCE_COUNT_FALSE", "groupByFields": ["resource.label.host"]}]}},
  {"displayName": "Server errors (5xx)",
   "conditionThreshold": {"filter": "metric.type=\"run.googleapis.com/request_count\" AND resource.type=\"cloud_run_revision\" AND resource.label.service_name=\"$SERVICE\" AND metric.label.response_code_class=\"5xx\"",
     "comparison": "COMPARISON_GT", "thresholdValue": 5, "duration": "0s",
     "aggregations": [{"alignmentPeriod": "300s", "perSeriesAligner": "ALIGN_SUM"}]}}],
 "notificationChannels": ["$channel"]}
JSON
    echo "  alert policy '$SERVICE down' created (emails $ALERT_EMAIL)"
  fi
}

step=${1:-all}
if [ "$step" = all ]; then
  for s in apis sql bucket secrets images vm migrate api monitor; do echo "== $s"; "$s"; done
else
  "$step"
fi
