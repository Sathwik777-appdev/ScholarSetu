"""Checks an officer's sanction against the scheme's rules (ARCHITECTURE.md §6.5; amounts live in rules/*.json).

Each instalment names the component of the rules' "amounts" it pays. A fixed amount caps the instalment;
a monthly amount caps it at rate x months; an "actual cost" item (tuition, fees) needs an evidence note.
Anything else is a violation, which the officer may override only with a recorded reason.
"""

from decimal import Decimal
from typing import Any


def _component(amounts: dict[str, Any], path: str) -> tuple[Any, str] | None:
    head, _, tail = path.partition(".")
    item = amounts.get(head)
    if item is None:
        return None
    value, unit = item.get("value"), str(item.get("unit", ""))
    if tail:
        if not isinstance(value, dict) or tail not in value:
            return None
        value = value[tail]
    return value, unit


def check_instalments(amounts: dict[str, Any], instalments: list) -> list[str]:
    """Return human-readable violations (empty = within the rules)."""
    problems: list[str] = []
    for n, inst in enumerate(instalments, start=1):
        found = _component(amounts, inst.component)
        if found is None:
            problems.append(f"Instalment {n}: '{inst.component}' is not an amount in this scheme's rules "
                            f"(known: {', '.join(sorted(amounts))})")
            continue
        value, unit = found
        amount = Decimal(str(inst.amount))
        if isinstance(value, dict):
            problems.append(f"Instalment {n}: '{inst.component}' has several rates "
                            f"({', '.join(sorted(value))}); name one, e.g. '{inst.component}.{sorted(value)[0]}'")
        elif isinstance(value, (int, float)):
            monthly = "month" in unit.lower()
            if monthly and not inst.months:
                problems.append(f"Instalment {n}: '{inst.component}' is paid per month; give the number of months")
                continue
            cap = Decimal(str(value)) * (inst.months if monthly else 1)
            if amount > cap:
                problems.append(f"Instalment {n}: ₹{amount:,.0f} is above the rules' ₹{cap:,.0f} for "
                                f"'{inst.component}' ({unit})")
        elif not inst.evidence_note:
            problems.append(f"Instalment {n}: '{inst.component}' is paid at {value!r}; add an evidence note "
                            f"(e.g. the fee receipt number)")
    return problems
