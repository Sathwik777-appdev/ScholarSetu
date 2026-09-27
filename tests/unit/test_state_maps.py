"""Portal state maps: every portal code maps to a real canonical state; unknown codes are never guessed."""

import pytest

from app.adapters.portal import StateMap
from app.adapters.sync_service import shortest_path
from app.shared.types import CanonicalState


@pytest.mark.parametrize("folder", ["nsp", "sfmp", "nos"])
def test_state_map_loads_and_parks_unknown_codes(folder):
    state_map = StateMap.load(folder)
    assert state_map.states and all(isinstance(s, CanonicalState) for s in state_map.states.values())
    assert state_map.state("SOMETHING_NEW_FROM_THE_PORTAL") is None  # the caller parks it
    assert CanonicalState.DRAFT not in {state_map.state("")}


def test_nos_adapter_is_the_nos_portal():
    assert StateMap.load("nos").source.value == "NOS_PORTAL"


def test_a_jump_is_filled_in_along_valid_transitions_only():
    path = shortest_path(CanonicalState.SUBMITTED, CanonicalState.SANCTIONED)
    assert path == [CanonicalState.INSTITUTE_VERIFICATION, CanonicalState.AUTHORITY_VERIFICATION,
                    CanonicalState.SANCTIONED]
    assert shortest_path(CanonicalState.REJECTED, CanonicalState.SANCTIONED) is None  # rejection is final
