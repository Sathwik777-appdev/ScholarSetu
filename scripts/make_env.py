"""Create .env from .env.example with fresh random secrets.

    python3 scripts/make_env.py          # production-like: DEMO_MODE=false
    python3 scripts/make_env.py --demo   # local demo: DEMO_MODE=true

Refuses to overwrite an existing .env (use --force). Secrets are written to the file only, never printed.
"""

import argparse
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = {
    "JWT_SECRET": lambda: secrets.token_hex(32),
    "MINIO_ROOT_PASSWORD": lambda: secrets.token_hex(16),
    "PPRL_HMAC_KEY": lambda: secrets.token_hex(32),
    "SMS_GATEWAY_TOKEN": lambda: secrets.token_hex(24),
    "SKILL_SERVICE_TOKEN": lambda: secrets.token_hex(24),
    "DIGILOCKER_CLIENT_SECRET": lambda: secrets.token_hex(24),  # shared with the test DigiLocker (mocks)
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="enable DEMO_MODE (local demos only)")
    parser.add_argument("--force", action="store_true", help="overwrite an existing .env")
    parser.add_argument("--output", default=str(ROOT / ".env"))
    args = parser.parse_args()
    target = Path(args.output)
    if target.exists() and not args.force:
        print(f"{target} already exists; not overwritten (use --force).")
        return 1
    lines = []
    for line in (ROOT / ".env.example").read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and not line.lstrip().startswith("#"):
            if key in GENERATED and not value:
                value = GENERATED[key]()
            elif key == "DEMO_MODE":
                value = "true" if args.demo else "false"
            line = f"{key}={value}"
        lines.append(line)
    target.write_text("\n".join(lines) + "\n")
    target.chmod(0o600)
    print(f"Wrote {target} (DEMO_MODE={'true' if args.demo else 'false'}); secrets generated, not shown.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
