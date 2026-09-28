"""Mock PFMS / NPCI mapper. Accounts are per Aadhaar vault reference; unknown references return 404.

The /_admin endpoints are mock-only: they let a demo or a test simulate the student fixing the
problem at the bank (e.g. getting the account Aadhaar-seeded).
"""

import uuid

from fastapi import APIRouter, HTTPException

from synthetic_data import BANK_ACCOUNTS, PAYMENTS

router = APIRouter()


def _account(aadhaar_ref: str) -> dict:
    account = BANK_ACCOUNTS.get(aadhaar_ref)
    if account is None:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return account


@router.get("/npci/mapper/{aadhaar_ref}")
def npci_mapper(aadhaar_ref: str):
    """NPCI Aadhaar mapper: is this Aadhaar seeded to a bank account for DBT?"""
    account = _account(aadhaar_ref)
    if not account["seeded"]:
        return {"aadhaar_ref": aadhaar_ref, "seeded": False}
    return {"aadhaar_ref": aadhaar_ref, "seeded": True, "bank_name": account["bank_name"], "iin": account["iin"],
            "account_masked": account["account_masked"]}


@router.post("/dbt/verify-account")
def verify_account(payload: dict):
    account = _account(payload.get("aadhaar_ref", ""))
    return {"account_status": account["status"], "account_holder_name": account["holder_name"],
            "account_type": account["type"], "ifsc": account["ifsc"], "account_masked": account["account_masked"]}


@router.post("/dbt/initiate-payment")
def initiate_payment(payload: dict):
    # Idempotent on the caller's reference, like a real payment rail: a resent request returns the same
    # transaction instead of paying twice.
    reference = payload.get("reference")
    if reference:
        for existing in PAYMENTS.values():
            if existing["reference"] == reference:
                return {"txn_ref": existing["txn_ref"], "status": "PENDING"}
    account = _account(payload.get("aadhaar_ref", ""))
    txn_ref = f"PFMS-{uuid.uuid4().hex[:12].upper()}"
    if not account["seeded"]:
        status, code = "FAILED", "AADHAAR_NOT_SEEDED"
    elif account["status"] != "ACTIVE":
        status, code = "FAILED", "INACTIVE_ACCOUNT" if account["status"] == "DORMANT" else "ACCOUNT_BLOCKED"
    else:
        status, code = "SUCCESS", None
    PAYMENTS[txn_ref] = {"txn_ref": txn_ref, "status": status, "failure_code": code,
                         "amount": payload.get("amount"), "reference": payload.get("reference")}
    return {"txn_ref": txn_ref, "status": "PENDING"}


@router.get("/dbt/status/{txn_ref}")
def payment_status(txn_ref: str):
    if txn_ref not in PAYMENTS:
        raise HTTPException(status_code=404, detail="NOT_FOUND")
    return PAYMENTS[txn_ref]


@router.post("/_admin/accounts/{aadhaar_ref}")
def admin_update_account(aadhaar_ref: str, payload: dict):
    account = _account(aadhaar_ref)
    for key in ("seeded", "status", "holder_name"):
        if key in payload:
            account[key] = payload[key]
    return account
