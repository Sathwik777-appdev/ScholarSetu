"""Claims that were false (validation report F1, F2, F3) must not come back into the docs or the UIs."""

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CHECKED = [ROOT / "README.md", ROOT / "docs" / "PITCH_AND_DEFENSE.md", ROOT / "docs" / "demo-script.md",
           ROOT / "apps" / "mobile" / "README.md",
           *sorted((ROOT / "apps" / "console" / "src").rglob("*.ts*")),
           *sorted((ROOT / "apps" / "mobile" / "lib").rglob("*.dart"))]

FORBIDDEN = {
    r"double metaphone": "no Double Metaphone exists in the resolver",
    r"matches 100%": "the resolver never reported this",
    r"\b5\s?ms\b|5 milliseconds": "never measured",
    r"4 million": "unsourced statistic",
    r"30% (of eligible )?(students )?fall": "unsourced statistic",
    r"capacitor": "the mobile app is Flutter",
    r"committed to ledger": "the console shows the ledger event id the API returned instead",
    r"bhashini mock": "there is no Bhashini mock",
    r"npci seeded & verified": "DBT status comes from the API, not a fixed label",
}


@pytest.mark.parametrize("path", CHECKED, ids=lambda p: str(p.relative_to(ROOT)))
def test_no_known_false_claims(path):
    text = path.read_text(encoding="utf-8").lower()
    found = {why for pattern, why in FORBIDDEN.items() if re.search(pattern, text)}
    assert not found, f"{path.name}: {found}"


def test_readme_documents_the_real_mock_paths():
    readme = (ROOT / "README.md").read_text()
    for path in ("/uidai", "/pfms/npci", "/digilocker", "/edistrict", "/udise"):
        assert f"`{path}" in readme
    assert ":8100/aadhaar" not in readme and ":8100/npci" not in readme
