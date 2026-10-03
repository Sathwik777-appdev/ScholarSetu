"""The power manager's idle decision (deploy/gcp/power-manager/main.py), with Google's APIs stubbed."""

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("google.auth")
pytest.importorskip("requests")

SPEC = importlib.util.spec_from_file_location(
    "power_manager", Path(__file__).resolve().parents[2] / "deploy" / "gcp" / "power-manager" / "main.py")
pm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pm)


class _Res:
    def __init__(self, body):
        self._body = body

    def json(self):
        return self._body


def _stub(monkeypatch, started_minutes_ago, real_requests):
    slept = []
    monkeypatch.setattr(pm, "_headers", lambda: {})
    monkeypatch.setattr(pm, "_state", lambda h: {"sleeping": False})
    started = (datetime.now(timezone.utc) - timedelta(minutes=started_minutes_ago)).isoformat()
    monkeypatch.setattr(pm.requests, "get", lambda *a, **k: _Res({"lastStartTimestamp": started}))
    monkeypatch.setattr(pm, "real_requests", lambda h, m: real_requests)
    monkeypatch.setattr(pm, "do_sleep", lambda: slept.append(True) or {"state": "sleeping"})
    return slept


def test_a_just_woken_system_is_not_put_back_to_sleep(monkeypatch):
    slept = _stub(monkeypatch, started_minutes_ago=8, real_requests=0)
    assert pm.check_idle()["action"] == "stay_awake" and slept == []


def test_an_idle_system_sleeps(monkeypatch):
    slept = _stub(monkeypatch, started_minutes_ago=90, real_requests=0)
    assert pm.check_idle()["action"] == "sleeping" and slept == [True]


def test_a_used_system_stays_awake(monkeypatch):
    slept = _stub(monkeypatch, started_minutes_ago=90, real_requests=3)
    assert pm.check_idle()["action"] == "stay_awake" and slept == []


def test_any_error_keeps_it_awake(monkeypatch):
    slept = _stub(monkeypatch, started_minutes_ago=90, real_requests=0)

    def boom(*a, **k):
        raise RuntimeError("logging API down")
    monkeypatch.setattr(pm, "real_requests", boom)
    assert pm.check_idle()["action"] == "stay_awake" and slept == []


def _wake_stub(monkeypatch, policy, sql_state, vm_status):
    calls = []
    monkeypatch.setattr(pm, "_headers", lambda: {})
    monkeypatch.setattr(pm, "_state", lambda h: {"sleeping": False, "cloud_sql": {"policy": policy, "state": sql_state},
                                                 "vm": {"status": vm_status}})
    for verb in ("patch", "post", "get"):
        monkeypatch.setattr(pm.requests, verb, lambda *a, _v=verb, **k: calls.append(_v) or _Res({}))
    monkeypatch.setattr(pm.time, "sleep", lambda s: calls.append("sleep"))
    return calls


def test_a_wake_while_the_database_is_starting_answers_at_once(monkeypatch):
    calls = _wake_stub(monkeypatch, "ALWAYS", "PENDING_CREATE", "PROVISIONING")
    assert pm.do_wake() == {"state": "waking", "already": True, "complete": True}
    assert calls == []  # nothing patched, nothing waited for


def test_a_wake_when_everything_is_up_says_so(monkeypatch):
    calls = _wake_stub(monkeypatch, "ALWAYS", "RUNNABLE", "RUNNING")
    assert pm.do_wake()["state"] == "awake" and calls == []


def test_a_wake_while_asleep_still_starts_everything(monkeypatch):
    calls = _wake_stub(monkeypatch, "NEVER", "STOPPED", "TERMINATED")
    monkeypatch.setattr(pm.requests, "patch", lambda *a, **k: calls.append("patch") or type("R", (), {"status_code": 200, "ok": True})())
    monkeypatch.setattr(pm.requests, "post", lambda *a, **k: calls.append("post") or type("R", (), {"status_code": 200, "ok": True})())
    monkeypatch.setattr(pm, "_set_alert", lambda h, e: "enabled")
    result = pm.do_wake()
    assert "patch" in calls and "post" in calls and result["state"] == "waking" and "already" not in result
