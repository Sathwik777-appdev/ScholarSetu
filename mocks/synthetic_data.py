import random
from typing import Dict, Any, List
from faker import Faker

fake = Faker('en_IN')

# In-memory database
db: Dict[str, Any] = {
    "students": [],
    "institutions": [],
    "applications": {},
    "certificates": {},
    "documents": {},
    "payments": {}
}

def generate_synthetic_data():
    tribes = ["Santal", "Gond", "Bhil", "Munda", "Oraon", "Mina", "Ho", "Kharia"]
    districts = [
        "Ranchi", "Dumka", "Khunti", "Gumla", "Mayurbhanj", 
        "Sundargarh", "Korba", "Bastar", "Mandla", "Jhabua", 
        "Palghar", "Banswara"
    ]
    states = ["Jharkhand", "Odisha", "Chhattisgarh", "Madhya Pradesh", "Maharashtra", "Rajasthan"]
    
    # Pre-seeded Persona
    sunita = {
        "id": "ST1001",
        "first_name": "Sunita",
        "last_name": "Hansda",
        "gender": "F",
        "dob": "2002-05-14",
        "tribe": "Santal",
        "state": "Jharkhand",
        "district": "Dumka",
        "aadhaar": "123456789012",
        "apaar_id": "AP1234567890",
        "phone": "9876543210"
    }
    db["students"].append(sunita)
    
    rahul = {
        "id": "ST1002",
        "first_name": "Rahul",
        "last_name": "Hansda",
        "gender": "M",
        "dob": "2008-08-20",
        "tribe": "Santal",
        "state": "Jharkhand",
        "district": "Dumka",
        "aadhaar": "210987654321",
        "apaar_id": "AP2109876543",
        "phone": "9876543210"
    }
    db["students"].append(rahul)
    
    # Generate random students
    for i in range(18):
        tribe = random.choice(tribes)
        state = random.choice(states)
        district = random.choice(districts)
        
        student = {
            "id": f"ST200{i}",
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "gender": random.choice(["M", "F"]),
            "dob": fake.date_of_birth(minimum_age=10, maximum_age=25).isoformat(),
            "tribe": tribe,
            "state": state,
            "district": district,
            "aadhaar": str(fake.random_number(digits=12, fix_len=True)),
            "apaar_id": f"AP{fake.random_number(digits=10, fix_len=True)}",
            "phone": str(fake.random_number(digits=10, fix_len=True))
        }
        db["students"].append(student)

def get_student(ref: str):
    for student in db["students"]:
        if student["id"] == ref or student["aadhaar"] == ref or student["apaar_id"] == ref:
            return student
    return None
