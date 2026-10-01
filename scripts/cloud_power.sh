#!/usr/bin/env bash
# ScholarSetu Cloud Power & Cost Optimization Controller
# Controls Cloud SQL, Compute Engine VM, and Cloud Run sleep/wake states to minimize GCP billing.
#
# Usage:
#   ./scripts/cloud_power.sh status          # Check running status & estimated costs
#   ./scripts/cloud_power.sh off             # Shut down VM & Cloud SQL (drops compute cost to $0)
#   ./scripts/cloud_power.sh on              # Turn ON VM & Cloud SQL when needed for demos/testing
#   ./scripts/cloud_power.sh remove-nat      # Remove idle Cloud NAT gateway to save ~$32/month permanently

set -euo pipefail

PROJECT=${PROJECT:-trisphere-4b121}
REGION=${REGION:-asia-south1}
ZONE=${ZONE:-asia-south1-a}
VM=${VM:-scholarsetu-backend-demo}
SQL_INSTANCE=${SQL_INSTANCE:-scholarsetu-db}
ROUTER=${ROUTER:-scholarsetu-router}
NAT=${NAT:-scholarsetu-nat}
CLOUD_RUN_SERVICE=${CLOUD_RUN_SERVICE:-scholarsetu-api}

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
BLUE="\033[0;34m"
NC="\033[0m"

log_info() { echo -e "${BLUE}ℹ${NC} $1"; }
log_success() { echo -e "${GREEN}✔${NC} $1"; }
log_warn() { echo -e "${YELLOW}⚠${NC} $1"; }
log_error() { echo -e "${RED}✖${NC} $1"; }

cmd_status() {
  echo -e "\n${BOLD}=== ScholarSetu GCP Resource & Cost Status (Project: ${PROJECT}) ===${NC}\n"

  # 1. Cloud SQL
  local sql_status
  sql_status=$(gcloud sql instances describe "$SQL_INSTANCE" --project "$PROJECT" --format='value(settings.activationPolicy)' 2>/dev/null || echo "NOT_FOUND")
  local sql_state
  sql_state=$(gcloud sql instances describe "$SQL_INSTANCE" --project "$PROJECT" --format='value(state)' 2>/dev/null || echo "UNKNOWN")
  
  if [ "$sql_status" = "ALWAYS" ] && [ "$sql_state" = "RUNNABLE" ]; then
    echo -e "  Cloud SQL (${SQL_INSTANCE}):         ${GREEN}${BOLD}RUNNING${NC} (Billing ~\$25-\$35/mo)"
  elif [ "$sql_status" = "NEVER" ]; then
    echo -e "  Cloud SQL (${SQL_INSTANCE}):         ${YELLOW}${BOLD}SUSPENDED (SLEEPING)${NC} (Compute cost: ${GREEN}\$0${NC})"
  else
    echo -e "  Cloud SQL (${SQL_INSTANCE}):         ${YELLOW}${sql_state} (${sql_status})${NC}"
  fi

  # 2. Compute Engine VM
  local vm_status
  vm_status=$(gcloud compute instances describe "$VM" --zone "$ZONE" --project "$PROJECT" --format='value(status)' 2>/dev/null || echo "NOT_FOUND")
  
  if [ "$vm_status" = "RUNNING" ]; then
    echo -e "  Backend VM (${VM}):       ${GREEN}${BOLD}RUNNING${NC} (Billing ~\$15-\$20/mo)"
  elif [ "$vm_status" = "TERMINATED" ] || [ "$vm_status" = "STOPPED" ]; then
    echo -e "  Backend VM (${VM}):       ${YELLOW}${BOLD}STOPPED (SLEEPING)${NC} (Compute cost: ${GREEN}\$0${NC})"
  else
    echo -e "  Backend VM (${VM}):       ${YELLOW}${vm_status}${NC}"
  fi

  # 3. Cloud NAT
  local nat_exists
  nat_exists=$(gcloud compute routers nats list --router="$ROUTER" --region="$REGION" --project="$PROJECT" --format='value(name)' 2>/dev/null || true)
  if [ -n "$nat_exists" ]; then
    echo -e "  Cloud NAT (${NAT}):             ${RED}${BOLD}ACTIVE (Fixed fee ~\$32.40/mo even when idle)${NC}"
  else
    echo -e "  Cloud NAT (${NAT}):             ${GREEN}${BOLD}REMOVED${NC} (Saved ~\$32.40/mo)"
  fi

  # 4. Cloud Run
  echo -e "  Cloud Run (${CLOUD_RUN_SERVICE}):        ${GREEN}${BOLD}SERVERLESS${NC} (Auto-scales to 0; costs \$0 when no traffic)"

  echo -e "\n${BOLD}Quick Cost Actions:${NC}"
  echo "  Turn OFF (sleep):   ./scripts/cloud_power.sh off   (or 'make cloud-sleep')"
  echo "  Turn ON (wake):     ./scripts/cloud_power.sh on    (or 'make cloud-wake')"
  echo "  Remove Cloud NAT:   ./scripts/cloud_power.sh remove-nat"
  echo ""
}

cmd_off() {
  echo -e "\n${BOLD}Stopping ScholarSetu resources to eliminate compute billing...${NC}\n"

  # 1. Stop VM
  log_info "Stopping Backend VM (${VM})..."
  if gcloud compute instances stop "$VM" --zone "$ZONE" --project "$PROJECT" --quiet; then
    log_success "Backend VM stopped. VM compute cost is now \$0."
  else
    log_warn "Could not stop VM (may already be stopped)."
  fi

  # 2. Suspend Cloud SQL
  log_info "Setting Cloud SQL (${SQL_INSTANCE}) activation policy to NEVER (sleep)..."
  if gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=NEVER --project "$PROJECT" --quiet; then
    log_success "Cloud SQL suspended. Database compute cost is now \$0."
  else
    log_warn "Could not suspend Cloud SQL."
  fi

  echo -e "\n${GREEN}${BOLD}All ScholarSetu compute resources are now in SLEEP mode!${NC}"
  echo "Your hourly compute billing for ScholarSetu has dropped to \$0."
  echo "Run './scripts/cloud_power.sh on' whenever you want to test or demo."
}

cmd_on() {
  echo -e "\n${BOLD}Waking up ScholarSetu resources...${NC}\n"

  # 1. Start Cloud SQL
  log_info "Setting Cloud SQL (${SQL_INSTANCE}) activation policy to ALWAYS (waking up)..."
  gcloud sql instances patch "$SQL_INSTANCE" --activation-policy=ALWAYS --project "$PROJECT" --quiet
  log_success "Cloud SQL activation initiated."

  # 2. Start VM
  log_info "Starting Backend VM (${VM})..."
  gcloud compute instances start "$VM" --zone "$ZONE" --project "$PROJECT" --quiet
  log_success "Backend VM started."

  # 3. Wait for readiness
  log_info "Waiting for Cloud SQL and VM containers to become healthy (approx 30-45s)..."
  for i in $(seq 1 30); do
    if curl -sf --max-time 3 "https://${CLOUD_RUN_SERVICE}-906769842576.${REGION}.run.app/health/ready" >/dev/null 2>&1; then
      echo ""
      log_success "ScholarSetu API is LIVE and ready!"
      curl -s "https://${CLOUD_RUN_SERVICE}-906769842576.${REGION}.run.app/health/ready"
      echo ""
      return 0
    fi
    printf "."
    sleep 3
  done

  echo ""
  log_info "Services are starting up. Check status anytime with './scripts/cloud_power.sh status'"
}

cmd_remove_nat() {
  echo -e "\n${BOLD}Optimizing Network: Eliminating Cloud NAT (\$32.40/month cost)...${NC}\n"
  
  # Check if VM has an external IP
  local has_ext_ip
  has_ext_ip=$(gcloud compute instances describe "$VM" --zone "$ZONE" --project "$PROJECT" --format='value(networkInterfaces[0].accessConfigs[0].natIP)' 2>/dev/null || true)

  if [ -z "$has_ext_ip" ]; then
    log_info "Assigning an ephemeral external IP to VM ${VM} so it has direct outbound internet without NAT..."
    if ! gcloud compute instances add-access-config "$VM" --zone "$ZONE" --project "$PROJECT" --quiet; then
      log_error "Could not give the VM a public IP; Cloud NAT is kept (without either the VM has no internet)."
      exit 1
    fi
    log_success "VM now has direct outbound internet access."
  else
    log_info "VM already has an external IP access config."
  fi

  # Inbound stays closed: SSH only through IAP, RDP and public SSH denied (same rules as deploy.sh vm).
  gcloud compute firewall-rules describe scholarsetu-ssh-iap-only --project "$PROJECT" >/dev/null 2>&1 || \
    gcloud compute firewall-rules create scholarsetu-ssh-iap-only --project "$PROJECT" --network default \
      --direction INGRESS --priority 900 --allow tcp:22 --source-ranges 35.235.240.0/20 --target-tags scholarsetu-backend
  gcloud compute firewall-rules describe scholarsetu-deny-public-admin --project "$PROJECT" >/dev/null 2>&1 || \
    gcloud compute firewall-rules create scholarsetu-deny-public-admin --project "$PROJECT" --network default \
      --direction INGRESS --priority 950 --action DENY --rules tcp:22,tcp:3389 --source-ranges 0.0.0.0/0 \
      --target-tags scholarsetu-backend

  # Delete Cloud NAT
  log_info "Deleting Cloud NAT gateway (${NAT}) to stop the \$32.40/month charge..."
  if gcloud compute routers nats delete "$NAT" --router="$ROUTER" --region="$REGION" --project "$PROJECT" --quiet 2>/dev/null; then
    log_success "Cloud NAT (${NAT}) deleted. You saved ~\$32.40 per month!"
  else
    log_warn "Cloud NAT was not found or already deleted."
  fi

  # Delete Router
  log_info "Deleting Cloud Router (${ROUTER})..."
  gcloud compute routers delete "$ROUTER" --region="$REGION" --project "$PROJECT" --quiet 2>/dev/null || true
  log_success "Network optimization complete. \$32.40/month Cloud NAT fee eliminated!"
}

case "${1:-status}" in
  status) cmd_status ;;
  off|sleep|stop) cmd_off ;;
  on|wake|start) cmd_on ;;
  remove-nat) cmd_remove_nat ;;
  *)
    echo "Usage: $0 {status|off|on|remove-nat}"
    exit 1
    ;;
esac
