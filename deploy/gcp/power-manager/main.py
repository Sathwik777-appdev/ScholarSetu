"""ScholarSetu power manager (hosted demo only): puts the database and backend VM to sleep when nobody uses the
demo, and wakes them when someone does.

Private: Cloud Run IAM admits only Cloud Scheduler (idle check, nightly sleep) and the API (wake on a request
that found the database asleep). It runs as its own service account, allowed to start/stop one VM, change the
Cloud SQL activation policy, read request logs and switch the downtime alert; nothing else.

    POST /wake        database ALWAYS, VM started, downtime alert re-enabled
    POST /sleep       VM stopped, database NEVER, downtime alert paused (so a sleeping demo emails no one)
    POST /check-idle  sleep when the API served no real requests (uptime probes excluded) in IDLE_MINUTES
    GET  /status      current state
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import google.auth
import requests
from fastapi import FastAPI
from google.auth.transport.requests import Request

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("power-manager")

app = FastAPI(title="ScholarSetu power manager", docs_url=None, redoc_url=None)

PROJECT = os.environ.get("PROJECT", "trisphere-4b121")
ZONE = os.environ.get("ZONE", "asia-south1-a")
VM = os.environ.get("VM", "scholarsetu-backend-demo")
SQL_INSTANCE = os.environ.get("SQL_INSTANCE", "scholarsetu-db")
API_SERVICE = os.environ.get("API_SERVICE_NAME", "scholarsetu-api")
IDLE_MINUTES = int(os.environ.get("IDLE_MINUTES", "30"))
TIMEOUT = 15

SQL_URL = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{SQL_INSTANCE}"
VM_URL = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT}/zones/{ZONE}/instances/{VM}"
MONITORING = f"https://monitoring.googleapis.com/v3/projects/{PROJECT}"
LOGGING = "https://logging.googleapis.com/v2/entries:list"
ALERT_NAME = f"{API_SERVICE} down"  # created by deploy.sh `monitor`
# Uptime probes keep hitting /health/ready; they are not people using the demo.
UPTIME_AGENT = "GoogleStackdriverMonitoring-UptimeChecks"


def _headers() -> dict[str, str]:
    credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    return {"Authorization": f"Bearer {credentials.token}", "Content-Type": "application/json"}


def _set_alert(headers: dict, enabled: bool) -> str:
    """Pause the downtime alert while asleep; re-enable it on wake. Returns what happened."""
    res = requests.get(f"{MONITORING}/alertPolicies", headers=headers, params={"filter": f'display_name="{ALERT_NAME}"'},
                       timeout=TIMEOUT)
    policies = res.json().get("alertPolicies", []) if res.status_code == 200 else []
    if not policies:
        return "no alert policy"
    for policy in policies:
        requests.patch(f"https://monitoring.googleapis.com/v3/{policy['name']}", headers=headers,
                       params={"updateMask": "enabled"}, json={"enabled": enabled}, timeout=TIMEOUT)
    return "enabled" if enabled else "paused"


def _state(headers: dict) -> dict[str, Any]:
    sql = requests.get(SQL_URL, headers=headers, timeout=TIMEOUT)
    vm = requests.get(VM_URL, headers=headers, timeout=TIMEOUT)
    policy = sql.json().get("settings", {}).get("activationPolicy", "UNKNOWN") if sql.ok else "UNKNOWN"
    vm_status = vm.json().get("status", "UNKNOWN") if vm.ok else "UNKNOWN"
    return {"sleeping": policy == "NEVER" and vm_status in ("TERMINATED", "STOPPED", "STOPPING"),
            "cloud_sql": {"policy": policy, "state": sql.json().get("state", "UNKNOWN") if sql.ok else "UNKNOWN"},
            "vm": {"status": vm_status}}


WAKE_PATIENCE_SECONDS = 90  # within Cloud Run's 120 s request timeout


def do_wake() -> dict[str, Any]:
    """Start the database and the VM. A wake that arrives while a sleep is still in progress must not be lost:
    Cloud SQL answers 409 while its previous operation runs, and a VM that is still stopping ignores a start,
    so both are retried until they take or WAKE_PATIENCE_SECONDS pass."""
    headers = _headers()
    deadline = time.monotonic() + WAKE_PATIENCE_SECONDS
    sql = requests.patch(SQL_URL, headers=headers, json={"settings": {"activationPolicy": "ALWAYS"}}, timeout=TIMEOUT)
    while sql.status_code == 409 and time.monotonic() < deadline:
        time.sleep(10)
        sql = requests.patch(SQL_URL, headers=headers, json={"settings": {"activationPolicy": "ALWAYS"}},
                             timeout=TIMEOUT)
    status = requests.get(VM_URL, headers=headers, timeout=TIMEOUT).json().get("status")
    while status in ("STOPPING", "SUSPENDING") and time.monotonic() < deadline:
        time.sleep(10)
        status = requests.get(VM_URL, headers=headers, timeout=TIMEOUT).json().get("status")
    vm = requests.post(f"{VM_URL}/start", headers=headers, timeout=TIMEOUT)
    alert = _set_alert(headers, True)
    logger.info("wake: SQL HTTP %s, VM was %s, start HTTP %s, alert %s", sql.status_code, status, vm.status_code, alert)
    return {"state": "waking", "sql_status": sql.status_code, "vm_status": vm.status_code, "alert": alert,
            "complete": sql.ok and vm.ok}


def do_sleep() -> dict[str, Any]:
    headers = _headers()
    alert = _set_alert(headers, False)
    vm = requests.post(f"{VM_URL}/stop", headers=headers, timeout=TIMEOUT)
    sql = requests.patch(SQL_URL, headers=headers, json={"settings": {"activationPolicy": "NEVER"}}, timeout=TIMEOUT)
    logger.info("sleep: VM HTTP %s, SQL HTTP %s, alert %s", vm.status_code, sql.status_code, alert)
    return {"state": "sleeping", "vm_status": vm.status_code, "sql_status": sql.status_code, "alert": alert}


def real_requests(headers: dict, minutes: int) -> int:
    """API requests in the last `minutes` that did not come from uptime probes (counted up to 50)."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    log_filter = (f'resource.type="cloud_run_revision" AND resource.labels.service_name="{API_SERVICE}" '
                  f'AND log_id("run.googleapis.com/requests") AND timestamp>="{since}" '
                  f'AND NOT httpRequest.userAgent:"{UPTIME_AGENT}"')
    res = requests.post(LOGGING, headers=headers, timeout=TIMEOUT,
                        json={"resourceNames": [f"projects/{PROJECT}"], "filter": log_filter, "pageSize": 50})
    res.raise_for_status()
    return len(res.json().get("entries", []))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "scholarsetu-power-manager"}


@app.get("/status")
def status() -> dict[str, Any]:
    return _state(_headers())


@app.post("/wake")
def wake() -> dict[str, Any]:
    return do_wake()


@app.post("/sleep")
def sleep() -> dict[str, Any]:
    return do_sleep()


@app.post("/check-idle")
def check_idle() -> dict[str, Any]:
    """Sleep when nobody has used the API for IDLE_MINUTES. Any error keeps everything awake."""
    try:
        headers = _headers()
        if _state(headers)["sleeping"]:
            return {"action": "none", "reason": "already asleep"}
        used = real_requests(headers, IDLE_MINUTES)
    except Exception as exc:  # noqa: BLE001 - never sleep on uncertainty
        logger.exception("idle check failed; staying awake")
        return {"action": "stay_awake", "reason": f"check failed: {type(exc).__name__}"}
    logger.info("idle check: %d real API request(s) in the last %d minutes", used, IDLE_MINUTES)
    if used:
        return {"action": "stay_awake", "real_requests": used, "minutes": IDLE_MINUTES}
    return {"action": "sleeping", "real_requests": 0, "minutes": IDLE_MINUTES, **do_sleep()}
