"""Rules as code: every rules/*.json is well-formed, cites its source, and behaves at its boundaries."""

import json
from pathlib import Path

import pytest
from json_logic import jsonLogic

from app.shared.types import SchemeType

RULES = sorted((Path(__file__).resolve().parents[2] / "rules").glob("*.json"))


def _vars(logic):
    if isinstance(logic, dict):
        for op, args in logic.items():
            if op == "var":
                yield args if isinstance(args, str) else args[0]
            else:
                yield from _vars(args)
    elif isinstance(logic, list):
        for item in logic:
            yield from _vars(item)


@pytest.mark.parametrize("path", RULES, ids=lambda p: p.name)
def test_rule_file_is_well_formed(path):
    table = json.loads(path.read_text())
    SchemeType(table["scheme"])
    assert table["version"] and table["effective_from"]
    for name, p in table["parameters"].items():
        assert {"value", "source", "verified_by_team"} <= p.keys(), name  # every value says where it came from
    for rule in table["rules"]:
        assert rule["failure_reason"] and rule.get("failure_reason_hi"), rule["id"]
        for var in _vars(rule["logic"]):
            if var.startswith("params."):
                assert var.split(".", 1)[1] in table["parameters"], f"{rule['id']} uses undefined {var}"


def test_post_matric_income_limit_is_inclusive_and_read_from_parameters():
    table = json.loads(next(p for p in RULES if p.name.startswith("post_matric")).read_text())
    rule = next(r for r in table["rules"] if r["id"] == "postm_income_limit")
    limit = table["parameters"][next(v for v in _vars(rule["logic"]) if v.startswith("params.")).split(".", 1)[1]]["value"]
    params = {k: v["value"] for k, v in table["parameters"].items()}
    assert jsonLogic(rule["logic"], {"claims": {"INCOME": {"annual_income": limit}}, "params": params})
    assert not jsonLogic(rule["logic"], {"claims": {"INCOME": {"annual_income": limit + 1}}, "params": params})


def test_no_python_eval_anywhere():
    core = Path(__file__).resolve().parents[2] / "services" / "core" / "app"
    offenders = [str(p) for p in core.rglob("*.py") if "eval(" in p.read_text().replace("literal_eval(", "")]
    assert offenders == []
