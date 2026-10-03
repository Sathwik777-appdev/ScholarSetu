#!/usr/bin/env bash
# ScholarSetu on Google Cloud, one environment at a time (demo or prod).
#
#   ENV=demo deploy/gcp/deploy.sh all        # everything, in order
#   ENV=demo deploy/gcp/deploy.sh <step>     # one step: apis sql bucket secrets images vm migrate api monitor power
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
    run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com monitoring.googleapis.com \
    cloudscheduler.googleapis.com
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
  # DigiLocker partner client secret. In mock mode it is shared with the test DigiLocker on the VM; going live,
  # replace its value with the secret DigiLocker issues (and set DIGILOCKER_MODE/API_URL/AUTHORIZE_URL/CLIENT_ID).
  put_secret digilocker-client-secret "$(rand 24)"
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
  # Outbound only: the VM has an ephemeral public IP (no Cloud NAT, which costs more than the VM) so it can pull
  # images, but nothing on it is reachable from the internet: SSH only through IAP, every other inbound port
  # closed except the mocks from Cloud Run's subnet. Private Google Access lets it reach Google APIs either way.
  g compute networks subnets update default --region "$REGION" --enable-private-ip-google-access >/dev/null
  g compute firewall-rules describe scholarsetu-ssh-iap-only >/dev/null 2>&1 || \
    g compute firewall-rules create scholarsetu-ssh-iap-only --network default --direction INGRESS --priority 900 \
      --allow tcp:22 --source-ranges 35.235.240.0/20 --target-tags scholarsetu-backend
  g compute firewall-rules describe scholarsetu-deny-public-admin >/dev/null 2>&1 || \
    g compute firewall-rules create scholarsetu-deny-public-admin --network default --direction INGRESS \
      --priority 950 --action DENY --rules tcp:22,tcp:3389 --source-ranges 0.0.0.0/0 --target-tags scholarsetu-backend
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
      --service-account "$SA_EMAIL" --scopes cloud-platform --tags scholarsetu-backend \
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
  # Officer sign-in codes by email (Microsoft 365). Add the mailbox's password once:
  #   printf %s "$PASSWORD" | gcloud secrets create scholarsetu-$ENV-smtp-password --data-file=-
  exists g secrets describe "scholarsetu-$ENV-smtp-password" && secrets+=",SMTP_PASSWORD=scholarsetu-$ENV-smtp-password:latest"
  # DigiLocker. With the MeriPehchaan sandbox secret stored, the API uses the sandbox (real DigiLocker sign-in);
  # otherwise the test DigiLocker on the VM. Add it once:
  #   printf %s "$SECRET" | gcloud secrets create scholarsetu-$ENV-digilocker-sandbox-secret --data-file=-
  local number public dl dl_mode dl_client
  if exists g secrets describe "scholarsetu-$ENV-digilocker-sandbox-secret"; then
    secrets+=",DIGILOCKER_CLIENT_SECRET=scholarsetu-$ENV-digilocker-sandbox-secret:latest"
    dl_mode=${DIGILOCKER_MODE:-sandbox}; dl_client=${DIGILOCKER_CLIENT_ID:-MNRNJVXE}
    DIGILOCKER_API_URL=${DIGILOCKER_API_URL:-https://dev-meripehchaan.dl6.in}
  else
    exists g secrets describe "scholarsetu-$ENV-digilocker-client-secret" && \
      secrets+=",DIGILOCKER_CLIENT_SECRET=scholarsetu-$ENV-digilocker-client-secret:latest"
    dl_mode=${DIGILOCKER_MODE:-mock}; dl_client=${DIGILOCKER_CLIENT_ID:-scholarsetu-$ENV}
  fi
  number=$(g projects describe "$PROJECT" --format='value(projectNumber)')
  public=https://$SERVICE-$number.$REGION.run.app
  dl="DIGILOCKER_MODE=$dl_mode,DIGILOCKER_CLIENT_ID=$dl_client,PUBLIC_BASE_URL=$public"
  [ -n "${DIGILOCKER_API_URL:-}" ] && dl+=",DIGILOCKER_API_URL=$DIGILOCKER_API_URL"
  [ -n "${DIGILOCKER_AUTHORIZE_URL:-}" ] && dl+=",DIGILOCKER_AUTHORIZE_URL=$DIGILOCKER_AUTHORIZE_URL"
  # Demo: a request that finds the database asleep asks the (private) power manager to wake everything.
  [ "$ENV" = demo ] && dl+=",POWER_MANAGER_URL=https://scholarsetu-power-$number.$REGION.run.app"
  echo --image "$REPO/scholarsetu-core:$TAG" --region "$REGION" --service-account "$SA_EMAIL" \
    --set-cloudsql-instances "$CONNECTION" --network default --subnet default --vpc-egress private-ranges-only \
    --set-secrets "$secrets" \
    --set-env-vars "DEMO_MODE=$DEMO_MODE,RUN_MIGRATIONS=false,OUTBOX_PUBLISHER_ENABLED=false,ADAPTER_SYNC_INTERVAL_SECONDS=0,RETENTION_INTERVAL_SECONDS=0,MOCK_SERVICE_URL=http://$(vm_ip):8100,MINIO_URL=https://storage.googleapis.com,MINIO_BUCKET=$BUCKET,ATTESTATION_PRIVATE_KEY_PATH=/secrets/attestation/key.pem,SLA_DEMO_SECONDS=3600,DATABASE_POOL_SIZE=3,DATABASE_MAX_OVERFLOW=2,GEMINI_MODEL=${GEMINI_MODEL:-gemini-3.8-flash},$dl" \
    --cpu 1 --memory 2Gi
}

migrate() {
  local job=scholarsetu-migrate-$ENV cmd="alembic upgrade head"
  [ "$ENV" = demo ] && cmd="alembic upgrade head && python /scripts/seed_demo.py --if-empty"
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

power() {
  # Demo only: sleep the VM and database when idle, wake them on use (deploy/gcp/power-manager).
  # Its own account may only start/stop this VM, change the Cloud SQL activation policy, read request logs and
  # switch the downtime alert. Only Cloud Scheduler (OIDC) and the API may call it; it is never public.
  [ "$ENV" = demo ] || { echo "power management is for the demo environment only"; return; }
  local psa=scholarsetu-power psa_email number url role=scholarsetuPowerManager job sched path verb
  psa_email=$psa@$PROJECT.iam.gserviceaccount.com
  number=$(g projects describe "$PROJECT" --format='value(projectNumber)')
  url=https://scholarsetu-power-$number.$REGION.run.app
  exists g iam service-accounts describe "$psa_email" || \
    g iam service-accounts create "$psa" --display-name "ScholarSetu power manager"
  local perms=cloudsql.instances.get,cloudsql.instances.update,logging.logEntries.list
  perms+=,monitoring.alertPolicies.get,monitoring.alertPolicies.list,monitoring.alertPolicies.update
  if exists g iam roles describe "$role"; then g iam roles update "$role" --permissions "$perms" --quiet >/dev/null
  else g iam roles create "$role" --title "ScholarSetu power manager" --permissions "$perms" >/dev/null; fi
  g projects add-iam-policy-binding "$PROJECT" --member "serviceAccount:$psa_email" \
    --role "projects/$PROJECT/roles/$role" --condition=None >/dev/null
  g compute instances add-iam-policy-binding "$VM" --zone "$ZONE" --member "serviceAccount:$psa_email" \
    --role roles/compute.instanceAdmin.v1 >/dev/null
  # --invoker-iam-check: without it Cloud Run serves the URL to anyone, whatever the IAM policy says.
  g run deploy scholarsetu-power --image "$REPO/scholarsetu-power:$TAG" --region "$REGION" \
    --service-account "$psa_email" --no-allow-unauthenticated --invoker-iam-check \
    --min-instances 0 --max-instances 1 --memory 256Mi --timeout 120 \
    --set-env-vars "PROJECT=$PROJECT,ZONE=$ZONE,VM=$VM,SQL_INSTANCE=$SQL_INSTANCE,API_SERVICE_NAME=$SERVICE"
  for member in "serviceAccount:$psa_email" "serviceAccount:$SA_EMAIL"; do  # the scheduler, and the API
    g run services add-iam-policy-binding scholarsetu-power --region "$REGION" --member "$member" \
      --role roles/run.invoker >/dev/null
  done
  for spec in "scholarsetu-auto-sleep-idle|*/15 * * * *|check-idle" "scholarsetu-night-safety-sleep|30 1 * * *|sleep"; do
    IFS='|' read -r job sched path <<<"$spec"
    verb=create; exists g scheduler jobs describe "$job" --location "$REGION" && verb=update
    g scheduler jobs "$verb" http "$job" --location "$REGION" --schedule "$sched" --time-zone Asia/Kolkata \
      --uri "$url/$path" --http-method POST --oidc-service-account-email "$psa_email" --oidc-token-audience "$url" >/dev/null
  done
  # The API's own account must not hold admin rights over the database or VMs.
  for role_name in roles/cloudsql.admin roles/compute.instanceAdmin.v1 roles/monitoring.viewer; do
    g projects remove-iam-policy-binding "$PROJECT" --member "serviceAccount:$SA_EMAIL" --role "$role_name" \
      --condition=None >/dev/null 2>&1 || true
  done
  echo "  power manager: $url (private)"
}

step=${1:-all}
if [ "$step" = all ]; then
  for s in apis sql bucket secrets images vm migrate api monitor power; do echo "== $s"; "$s"; done
else
  "$step"
fi
