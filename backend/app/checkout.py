"""Checks a customer's delivery details. Mirrors src/utils/validateCheckout.js:
the browser checks first for quick feedback, the server checks again because
anyone can send a request without using our form."""

import re

LIMITS = {"fullName": 80, "phone": 20, "email": 254, "commune": 60, "address": 200, "notes": 500}

NAME_PATTERN = re.compile(r"^(?:[^\W\d_]|[\s'.-])+$")  # letters, spaces, ' . -
EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PHONE_PATTERN = re.compile(r"^(?:\+213|00213|0)([567]\d{8})$")

# The 58 wilayas of Algeria, in official code order (code "01" is Adrar)
WILAYAS = [
    "Adrar", "Chlef", "Laghouat", "Oum El Bouaghi", "Batna", "Béjaïa", "Biskra", "Béchar",
    "Blida", "Bouira", "Tamanrasset", "Tébessa", "Tlemcen", "Tiaret", "Tizi Ouzou", "Alger",
    "Djelfa", "Jijel", "Sétif", "Saïda", "Skikda", "Sidi Bel Abbès", "Annaba", "Guelma",
    "Constantine", "Médéa", "Mostaganem", "M'Sila", "Mascara", "Ouargla", "Oran", "El Bayadh",
    "Illizi", "Bordj Bou Arréridj", "Boumerdès", "El Tarf", "Tindouf", "Tissemsilt", "El Oued",
    "Khenchela", "Souk Ahras", "Tipaza", "Mila", "Aïn Defla", "Naâma", "Aïn Témouchent",
    "Ghardaïa", "Relizane", "Timimoun", "Bordj Badji Mokhtar", "Ouled Djellal", "Béni Abbès",
    "In Salah", "In Guezzam", "Touggourt", "Djanet", "El M'Ghair", "El Meniaa",
]
WILAYA_BY_CODE = {f"{i + 1:02d}": name for i, name in enumerate(WILAYAS)}


def normalize_phone(value: str) -> str | None:
    match = PHONE_PATTERN.match(re.sub(r"[\s.\-()]", "", value))
    return f"0{match.group(1)}" if match else None


def validate_customer(c: dict[str, str]) -> dict[str, str]:
    """Returns {field: message} for every invalid field (empty when all is fine)."""
    errors = {}
    name = c["fullName"].strip()
    if len(name) < 3 or len(name) > LIMITS["fullName"] or not NAME_PATTERN.match(name):
        errors["fullName"] = "Please enter a valid full name."
    elif len(name.split()) < 2:
        errors["fullName"] = "Please enter your first and last name."

    if len(c["phone"]) > LIMITS["phone"] or not normalize_phone(c["phone"]):
        errors["phone"] = "Enter a valid mobile number, e.g. 0555 12 34 56."

    email = c["email"].strip()
    if len(email) > LIMITS["email"] or not EMAIL_PATTERN.match(email):
        errors["email"] = "Enter a valid email address, e.g. name@example.com."

    if c["wilaya"] not in WILAYA_BY_CODE:
        errors["wilaya"] = "Please select a valid wilaya."

    commune = c["commune"].strip()
    if len(commune) < 2 or len(commune) > LIMITS["commune"]:
        errors["commune"] = "Please enter your commune."

    address = c["address"].strip()
    if len(address) < 10 or len(address) > LIMITS["address"]:
        errors["address"] = "Please give a more detailed address (street, building, floor…)."

    if len(c["notes"].strip()) > LIMITS["notes"]:
        errors["notes"] = f"Notes must be under {LIMITS['notes']} characters."
    return errors
