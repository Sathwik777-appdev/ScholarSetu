import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import google.auth
from google.auth.transport.requests import Request
from google.cloud import monitoring_v3
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("power-manager")

app = FastAPI(title="ScholarSetu Cloud Power Manager")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT = os.environ.get("PROJECT", "trisphere-4b121")
REGION = os.environ.get("REGION", "asia-south1")
ZONE = os.environ.get("ZONE", "asia-south1-a")
VM = os.environ.get("VM", "scholarsetu-backend-demo")
SQL_INSTANCE = os.environ.get("SQL_INSTANCE", "scholarsetu-db")
API_SERVICE_NAME = os.environ.get("API_SERVICE_NAME", "scholarsetu-api")


def get_headers() -> Dict[str, str]:
    credentials, _ = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )
    credentials.refresh(Request())
    return {
        "Authorization": f"Bearer {credentials.token}",
        "Content-Type": "application/json",
    }


def do_wake() -> Dict[str, Any]:
    logger.info("Waking up Cloud SQL and VM...")
    headers = get_headers()
    
    # 1. Cloud SQL ALWAYS
    sql_url = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{SQL_INSTANCE}"
    sql_resp = requests.patch(sql_url, headers=headers, json={"settings": {"activationPolicy": "ALWAYS"}}, timeout=15)
    
    # 2. Compute VM Start
    vm_url = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT}/zones/{ZONE}/instances/{VM}/start"
    vm_resp = requests.post(vm_url, headers=headers, timeout=15)
    
    logger.info("Wake calls issued: SQL status=%s, VM status=%s", sql_resp.status_code, vm_resp.status_code)
    return {
        "sql_status": sql_resp.status_code,
        "vm_status": vm_resp.status_code,
        "state": "waking",
    }


def do_sleep() -> Dict[str, Any]:
    logger.info("Suspending Cloud SQL and stopping VM...")
    headers = get_headers()
    
    # 1. Compute VM Stop
    vm_url = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT}/zones/{ZONE}/instances/{VM}/stop"
    vm_resp = requests.post(vm_url, headers=headers, timeout=15)
    
    # 2. Cloud SQL NEVER
    sql_url = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{SQL_INSTANCE}"
    sql_resp = requests.patch(sql_url, headers=headers, json={"settings": {"activationPolicy": "NEVER"}}, timeout=15)
    
    logger.info("Sleep calls issued: VM status=%s, SQL status=%s", vm_resp.status_code, sql_resp.status_code)
    return {
        "vm_status": vm_resp.status_code,
        "sql_status": sql_resp.status_code,
        "state": "sleeping",
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok", "service": "scholarsetu-power-manager"}


@app.get("/status")
def status() -> Dict[str, Any]:
    headers = get_headers()
    
    # Cloud SQL
    sql_url = f"https://sqladmin.googleapis.com/sql/v1beta4/projects/{PROJECT}/instances/{SQL_INSTANCE}"
    sql_resp = requests.get(sql_url, headers=headers, timeout=10)
    sql_policy = "UNKNOWN"
    sql_state = "UNKNOWN"
    if sql_resp.status_code == 200:
        data = sql_resp.json()
        sql_policy = data.get("settings", {}).get("activationPolicy", "UNKNOWN")
        sql_state = data.get("state", "UNKNOWN")
        
    # VM
    vm_url = f"https://compute.googleapis.com/compute/v1/projects/{PROJECT}/zones/{ZONE}/instances/{VM}"
    vm_resp = requests.get(vm_url, headers=headers, timeout=10)
    vm_status_val = "UNKNOWN"
    if vm_resp.status_code == 200:
        vm_status_val = vm_resp.json().get("status", "UNKNOWN")
        
    is_sleeping = (sql_policy == "NEVER" and vm_status_val in ("TERMINATED", "STOPPED"))
    return {
        "sleeping": is_sleeping,
        "cloud_sql": {"policy": sql_policy, "state": sql_state},
        "vm": {"status": vm_status_val},
    }


@app.api_route("/wake", methods=["GET", "POST"])
def wake(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    background_tasks.add_task(do_wake)
    return {"message": "Wake sequence initiated. Cloud SQL and VM are starting up.", "status": "waking"}


@app.api_route("/sleep", methods=["GET", "POST"])
def sleep(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    background_tasks.add_task(do_sleep)
    return {"message": "Sleep sequence initiated. Cloud SQL and VM are being suspended to $0.", "status": "sleeping"}


@app.api_route("/check-idle", methods=["GET", "POST"])
def check_idle(background_tasks: BackgroundTasks) -> Dict[str, Any]:
    """Checks if there was any traffic on scholarsetu-api in the past 30 minutes. If 0, puts to sleep."""
    try:
        credentials, _ = google.auth.default()
        client = monitoring_v3.MetricServiceClient(credentials=credentials)
        now = datetime.now(timezone.utc)
        interval = monitoring_v3.TimeInterval(
            end_time={"seconds": int(now.timestamp())},
            start_time={"seconds": int((now - timedelta(minutes=30)).timestamp())},
        )
        
        project_name = f"projects/{PROJECT}"
        filter_str = (
            f'metric.type = "run.googleapis.com/request_count" AND '
            f'resource.labels.service_name = "{API_SERVICE_NAME}"'
        )
        
        results = client.list_time_series(
            request={
                "name": project_name,
                "filter": filter_str,
                "interval": interval,
                "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
            }
        )
        
        total_requests = 0
        for series in results:
            for point in series.points:
                total_requests += point.value.int64_value
                
        logger.info("Idle check: detected %d requests to %s in last 30 minutes", total_requests, API_SERVICE_NAME)
        
        if total_requests == 0:
            logger.info("Zero requests in last 30 minutes. Triggering automatic sleep...")
            background_tasks.add_task(do_sleep)
            return {
                "action": "sleeping",
                "reason": "zero_traffic_30m",
                "requests_last_30m": 0,
            }
        else:
            return {
                "action": "stay_awake",
                "reason": "active_traffic",
                "requests_last_30m": total_requests,
            }
    except Exception as e:
        logger.exception("Failed to query monitoring metrics: %s", e)
        return {"error": str(e), "action": "stay_awake"}
