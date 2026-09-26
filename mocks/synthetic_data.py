"""Synthetic people and per-source records for the mock government services.

Every mock answers from these records and returns 404 for anything it does not know, so
the core can tell "confirmed" from "no record". Demo personas match scripts/seed_demo.py.
"""

import random
from typing import Any, Dict, Optional

from faker import Faker

fake = Faker("en_IN")

db: Dict[str, Any] = {"students": []}

# ── Demo personas (ARCHITECTURE.md §14) ─────────────────────────────────────

SUNITA = {
    "id": "ST1001", "first_name": "Sunita", "last_name": "Hansda", "gender": "FEMALE", "dob": "2008-04-12",
    "father_name": "Babulal Hansda", "mother_name": "Marangmai Hansda", "tribe": "Santal",
    "state": "Jharkhand", "district": "Dumka",
    "aadhaar": "AREF-JH-0004912", "apaar_id": "APAAR-JH-2026-0812", "phone": "9876543210",
    "sources": {
        "uidai": {"name": "Sunita Hansda"},
        # Her caste certificate spells the surname "Hansdah" and carries no DOB or parent names,
        # so the identity link cannot be auto-confirmed (demo Scene 3).
        "caste": {"certificate_no": "JH/ST/2022/8821", "holder_name": "Sunita Hansdah", "category": "ST",
                  "tribe": "Santal", "pvtg": False, "issued_by": "Circle Officer, Dumka", "issue_date": "2022-06-14",
                  "status": "VALID"},
        "income": {"certificate_no": "JH/INC/2026/55120", "holder_name": "Sunita Hansda",
                   "father_name": "Babulal Hansda", "district": "Dumka", "annual_income": 120000,
                   "financial_year": "2026-27", "valid_until": "2027-03-31", "status": "VALID"},
        "domicile": {"certificate_no": "JH/DOM/2021/1044", "holder_name": "Sunita Hansda",
                     "father_name": "Babulal Hansda", "district": "Dumka", "state": "Jharkhand", "status": "VALID"},
        "digilocker": {
            "MARKSHEET_10": {"doc_id": "in.gov.jac-MARKSHEET_10-2026-109283", "issuer": "Jharkhand Academic Council",
                             "holder_name": "SUNITA HANSDA", "father_name": "BABULAL HANSDA",
                             "data": {"board": "JAC", "exam": "Class 10 (Matriculation)", "year": "2026",
                                      "result": "PASS", "percentage": 84.5}},
        },
        "udise": {"udise_code": "20140212345", "school_name": "Government High School, Dumka", "class": "10",
                  "academic_year": "2025-26", "status": "PASSED_OUT"},
        "aishe": {"aishe_code": "C-41290", "institution": "Dumka Government College",
                  "course": "Intermediate (Class 11) Science", "academic_year": "2026-27", "status": "ENROLLED"},
        "apaar": [{"academic_year": "2024-25", "grade": "9", "result": "PASS"},
                  {"academic_year": "2025-26", "grade": "10", "result": "PASS"}],
    },
}

RAHUL = {
    "id": "ST1002", "first_name": "Rahul", "last_name": "Hansda", "gender": "MALE", "dob": "2010-08-15",
    "father_name": "Babulal Hansda", "mother_name": "Marangmai Hansda", "tribe": "Santal",
    "state": "Jharkhand", "district": "Dumka",
    "aadhaar": "AREF-JH-0009914", "apaar_id": "APAAR-JH-2025-4192", "phone": "9876543211",
    "sources": {
        "uidai": {"name": "Rahul Hansda"},
        "caste": {"certificate_no": "JH/ST/2023/1177", "holder_name": "Rahul Hansda", "father_name": "Babulal Hansda",
                  "district": "Dumka", "category": "ST", "tribe": "Santal", "pvtg": False,
                  "issued_by": "Circle Officer, Dumka", "issue_date": "2023-05-02", "status": "VALID"},
        "income": {"certificate_no": "JH/INC/2026/55121", "holder_name": "Rahul Hansda",
                   "father_name": "Babulal Hansda", "district": "Dumka", "annual_income": 120000,
                   "financial_year": "2026-27", "valid_until": "2027-03-31", "status": "VALID"},
        "udise": {"udise_code": "20140212345", "school_name": "Government High School, Dumka", "class": "9",
                  "academic_year": "2026-27", "status": "ACTIVE"},
    },
}


def _random_person(i: int) -> dict:
    gender = random.choice(["MALE", "FEMALE"])
    first = fake.first_name_male() if gender == "MALE" else fake.first_name_female()
    last = random.choice(["Munda", "Oraon", "Soren", "Murmu", "Tudu", "Kisku", "Hembrom", "Marandi", "Bhil", "Gond"])
    return {
        "id": f"ST200{i}", "first_name": first, "last_name": last, "gender": gender,
        "dob": fake.date_of_birth(minimum_age=12, maximum_age=25).isoformat(),
        "father_name": f"{fake.first_name_male()} {last}", "mother_name": None,
        "tribe": random.choice(["Santal", "Gond", "Bhil", "Munda", "Oraon", "Ho"]),
        "state": "Jharkhand", "district": random.choice(["Ranchi", "Dumka", "Khunti", "Gumla"]),
        "aadhaar": f"AREF-SYN-{i:07d}", "apaar_id": f"APAAR-SYN-{i:06d}",
        "phone": str(fake.random_number(digits=10, fix_len=True)),
        "sources": {"uidai": {"name": f"{first} {last}"}},
    }


def generate_synthetic_data() -> None:
    random.seed(26238)
    Faker.seed(26238)
    db["students"] = [SUNITA, RAHUL] + [_random_person(i) for i in range(18)]


def get_student(ref: str) -> Optional[dict]:
    for student in db["students"]:
        if ref in (student["id"], student["aadhaar"], student["apaar_id"]):
            return student
    return None


def full_name(student: dict) -> str:
    return f"{student['first_name']} {student['last_name']}"
