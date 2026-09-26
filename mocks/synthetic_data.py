"""Synthetic people and per-source records for the mock government services.

Every mock answers from these records and returns 404 for anything it does not know, so
the core can tell "confirmed" from "no record". Demo personas match scripts/seed_demo.py.
"""

import random
from typing import Any, Dict, Optional

from faker import Faker

fake = Faker("en_IN")

db: Dict[str, Any] = {"students": []}

# PFMS / NPCI view of bank accounts, keyed by Aadhaar vault reference (reset by generate_synthetic_data).
BANK_ACCOUNTS: Dict[str, dict] = {}
PAYMENTS: Dict[str, dict] = {}
# Applications held on the three scholarship portals, in each portal's own status vocabulary.
PORTAL_APPS: Dict[str, Dict[str, dict]] = {"nsp": {}, "sfmp": {}, "nos": {}}

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
        "udise": {"udise_code": "20140212345", "school_name": "Government High School, Dumka", "class": "10",
                  "academic_year": "2026-27", "status": "ACTIVE"},
    },
}


# A student whose Post-Matric application lives on NSP; the NSP adapter imports it into the ledger.
SALKHAN = {
    "id": "ST1003", "first_name": "Salkhan", "last_name": "Soren", "gender": "MALE", "dob": "2007-12-01",
    "father_name": "Gopal Soren", "mother_name": None, "tribe": "Santal", "state": "Jharkhand", "district": "Dumka",
    "aadhaar": "AREF-JH-0005521", "apaar_id": "APAAR-JH-2026-5521", "phone": "9876543213",
    "sources": {"uidai": {"name": "Salkhan Soren"}},
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
    generate_enrolled_roster()
    random.seed(26238)
    Faker.seed(26238)
    db["students"] = [SUNITA, RAHUL, SALKHAN] + [_random_person(i) for i in range(18)]
    for portal in PORTAL_APPS.values():
        portal.clear()
    PORTAL_APPS["nsp"]["NSP-JH-2026-00417"] = {
        "app_id": "NSP-JH-2026-00417", "aadhaar_ref": SALKHAN["aadhaar"], "scheme": "POST_MATRIC",
        "academic_year": "2026-27", "status": "PENDING_INSTITUTE", "status_updated_at": "2026-09-10T10:00:00+05:30",
        "submitted_at": "2026-09-05T10:00:00+05:30", "remarks": "", "payments": [],
    }
    BANK_ACCOUNTS.clear()
    PAYMENTS.clear()
    # Demo Scene 4: Sunita's account exists and is active but is NOT Aadhaar-seeded for DBT.
    BANK_ACCOUNTS[SUNITA["aadhaar"]] = {"seeded": False, "status": "ACTIVE", "holder_name": "SUNITA HANSDA",
                                        "type": "SAVINGS", "bank_name": "State Bank of India", "iin": "508534",
                                        "ifsc": "SBIN0001234", "account_masked": "XXXXXX5678"}
    BANK_ACCOUNTS[SALKHAN["aadhaar"]] = {"seeded": True, "status": "ACTIVE", "holder_name": "SALKHAN SOREN",
                                         "type": "SAVINGS", "bank_name": "State Bank of India", "iin": "508534",
                                         "ifsc": "SBIN0001234", "account_masked": "XXXXXX5521"}
    BANK_ACCOUNTS[RAHUL["aadhaar"]] = {"seeded": True, "status": "ACTIVE", "holder_name": "RAHUL HANSDA",
                                       "type": "SAVINGS", "bank_name": "Jharkhand Rajya Gramin Bank", "iin": "607063",
                                       "ifsc": "SBIN0RRJRGB", "account_masked": "XXXXXX9914"}
    for person in db["students"][3:]:
        BANK_ACCOUNTS[person["aadhaar"]] = {"seeded": True, "status": "ACTIVE",
                                            "holder_name": full_name(person).upper(), "type": "SAVINGS",
                                            "bank_name": "State Bank of India", "iin": "508534",
                                            "ifsc": "SBIN0001234", "account_masked": "XXXXXX" + person["aadhaar"][-4:]}


def get_student(ref: str) -> Optional[dict]:
    for student in db["students"]:
        if ref in (student["id"], student["aadhaar"], student["apaar_id"]):
            return student
    return None


def full_name(student: dict) -> str:
    return f"{student['first_name']} {student['last_name']}"


# ── UDISE+ roster of enrolled ST students (for Reach Radar) ─────────────────

BLOCK_SCHOOLS = {
    "Dumka": [("20140212345", "Government High School, Dumka"), ("20140212399", "Project Girls High School, Dumka")],
    "Jama": [("20140300111", "Government High School, Jama"), ("20140300122", "Upgraded High School, Jama")],
    "Jarmundi": [("20140400211", "Government High School, Jarmundi")],
    "Kathikund": [("20140500311", "Eklavya Model Residential School, Kathikund")],
    "Shikaripara": [("20140600411", "Government High School, Shikaripara"),
                    ("20140600422", "Ashram School, Shikaripara")],
}
FIRST_NAMES = ["Sunil", "Anita", "Salomi", "Birsa", "Mangal", "Sonamuni", "Phulmani", "Baburam", "Lakhan", "Sita",
               "Rani", "Dulari", "Maino", "Somra", "Budhu", "Chunnu", "Sanjay", "Pradeep", "Rekha", "Pinky",
               "Parvati", "Jitu", "Sukhmati", "Hopna", "Talamai", "Ganesh", "Kiran", "Bahamuni", "Sagen", "Lukhi"]
SURNAMES = ["Hansda", "Murmu", "Soren", "Tudu", "Kisku", "Hembrom", "Marandi", "Baskey", "Besra", "Mardi"]
PVTG_SURNAMES = ["Pahariya", "Malto"]
ENROLLED_ST: list[dict] = []


def generate_enrolled_roster() -> None:
    rng = random.Random(8641)
    ENROLLED_ST.clear()
    ENROLLED_ST.append({"record_ref": "UDISE-REC-000001", "name": "Rahul Hansda", "dob": RAHUL["dob"],
                        "district": "Dumka", "block": "Dumka", "udise_code": "20140212345",
                        "school_name": "Government High School, Dumka", "class": 10, "pvtg": False,
                        "apaar_id": RAHUL["apaar_id"]})
    n = 2
    for block, schools in BLOCK_SCHOOLS.items():
        for _ in range(48):
            cls = rng.choice([9, 10, 11, 12])
            pvtg = rng.random() < 0.1
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(PVTG_SURNAMES if pvtg else SURNAMES)}"
            year = 2026 - (cls + 5)
            dob = f"{year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
            code, school = rng.choice(schools)
            ENROLLED_ST.append({"record_ref": f"UDISE-REC-{n:06d}", "name": name, "dob": dob, "district": "Dumka",
                                "block": block, "udise_code": code, "school_name": school, "class": cls,
                                "pvtg": pvtg, "apaar_id": f"APAAR-SYN-R{n:05d}" if rng.random() < 0.5 else None})
            n += 1


generate_enrolled_roster()
