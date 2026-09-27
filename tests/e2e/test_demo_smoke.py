"""End to end: the eight demo scenes against a running, freshly seeded demo stack.

Skipped unless SMOKE_BASE_URL is set (CI sets it after `docker compose up` and seeding)."""

import importlib.util
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(not os.environ.get("SMOKE_BASE_URL"), reason="needs a running demo stack")


def test_all_demo_scenes_pass():
    path = Path(__file__).resolve().parents[2] / "scripts" / "demo_smoke_test.py"
    spec = importlib.util.spec_from_file_location("demo_smoke_test", path)
    smoke = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(smoke)
    assert smoke.main() == 0
