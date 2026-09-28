"""The mock services' image installs only mocks/requirements.txt; the test suite runs with the core's
dependencies, so a missing mock dependency would pass every test and crash the deployed container."""

from pathlib import Path

REQUIREMENTS = Path(__file__).resolve().parents[2] / "mocks" / "requirements.txt"


def _names() -> set[str]:
    return {line.split("#")[0].strip().split("=")[0].split(">")[0].split("<")[0].lower()
            for line in REQUIREMENTS.read_text().splitlines() if line.split("#")[0].strip()}


def test_mock_image_installs_what_its_routes_need():
    # FastAPI Form(...) parameters (the test DigiLocker's sign-in page and token endpoint) need python-multipart.
    assert {"fastapi", "uvicorn", "faker", "python-multipart"} <= _names()
