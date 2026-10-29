"""Algerian delivery details: wilayas and mobile numbers.

Mirrors frontend/src/data/wilayas.js and src/utils/validateCheckout.js: the browser
checks first for quick feedback, the server checks again because anyone can send a
request without using our form.
"""

import re

# The 58 wilayas, in official code order (code "01" is Adrar)
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

# 05/06/07 + 8 digits, with an optional +213 / 00213 prefix instead of the 0
MOBILE_PATTERN = re.compile(r"^(?:\+213|00213|0)([567]\d{8})$")


def normalize_phone(value: str) -> str | None:
    """"+213 555-12.34 56" → "0555123456"; None if it isn't an Algerian mobile number."""
    match = MOBILE_PATTERN.match(re.sub(r"[\s.\-()]", "", value))
    return f"0{match.group(1)}" if match else None
