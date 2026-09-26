"""Scheme adapters (anti-corruption layer, ARCHITECTURE.md §6.2): one client per portal plus its state map."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

from app.config import settings
from app.shared.types import CanonicalState, PaymentState, SourceSystem
from app.verification.sources import SourceClient


@dataclass
class StateMap:
    source: SourceSystem
    states: dict[str, CanonicalState]
    payment_states: dict[str, PaymentState]

    @classmethod
    def load(cls, folder: str) -> "StateMap":
        data = yaml.safe_load((Path(settings.ADAPTERS_DIR) / folder / "state_map.yaml").read_text())
        if data.get("unknown_state_policy") != "park_and_alert":
            raise ValueError(f"{folder}/state_map.yaml must declare unknown_state_policy: park_and_alert")
        return cls(source=SourceSystem(data["source"]),
                   states={k: CanonicalState(v) for k, v in data["states"].items()},
                   payment_states={k: PaymentState(v) for k, v in data.get("payment_states", {}).items()})

    def state(self, raw: str) -> Optional[CanonicalState]:
        return self.states.get(raw)  # None = unknown: the caller parks it

    def payment_state(self, raw: str) -> Optional[PaymentState]:
        return self.payment_states.get(raw)


class PortalAdapter:
    def __init__(self, folder: str, path_prefix: str):
        self.map = StateMap.load(folder)
        self.prefix = path_prefix

    @property
    def source(self) -> SourceSystem:
        return self.map.source

    async def list_applications(self, client: SourceClient, aadhaar_ref: str) -> list[dict]:
        return await client.request("GET", f"{self.prefix}/students/{aadhaar_ref}/applications") or []

    async def get_payments(self, client: SourceClient, app_ref: str) -> list[dict]:
        return await client.request("GET", f"{self.prefix}/applications/{app_ref}/payments") or []


def default_adapters() -> list[PortalAdapter]:
    return [PortalAdapter("nsp", "/nsp"), PortalAdapter("sfmp", "/sfmp"), PortalAdapter("nos", "/nos")]
