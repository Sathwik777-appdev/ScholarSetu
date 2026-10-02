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
