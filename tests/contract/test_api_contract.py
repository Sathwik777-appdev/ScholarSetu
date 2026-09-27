"""The API promised in ARCHITECTURE.md §8 exists in the running app (same methods and paths)."""

import re
from pathlib import Path

from app.main import app

ARCH = (Path(__file__).resolve().parents[2] / "docs" / "ARCHITECTURE.md").read_text()


def _normalise(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{}", path.split("?")[0])


def _documented_routes() -> set[tuple[str, str]]:
    section = ARCH[ARCH.index("## 8."):ARCH.index("## 9.")]
    return {(m, _normalise(p)) for m, p in re.findall(r"^(GET|POST|PUT|PATCH|DELETE)\s+(/v1/\S+)", section, re.M)}


def test_every_documented_route_is_served():
    served = {(method.upper(), _normalise(path)) for path, operations in app.openapi()["paths"].items()
              for method in operations}
    documented = _documented_routes()
    assert len(documented) >= 25
    assert documented - served == set()
