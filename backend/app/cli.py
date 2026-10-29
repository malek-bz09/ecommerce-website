"""Command-line tasks.

    uv run python -m app.cli create-admin --email you@shop.dz --name "Your Name" [--role staff]
    uv run python -m app.cli seed     # add the sample products to an empty catalogue
"""

import argparse
import sys
from decimal import Decimal
from getpass import getpass

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.product import Product
from app.services.auth import save_admin

# The shop's starting catalogue. Photos are in frontend/public/<slug>.jpg.
SAMPLE_PRODUCTS = [
    ("burberry-check-collar-polo-navy", "Burberry Check Collar Polo", "tops", "8500", None, 6,
     "Navy cotton piqué polo with the signature beige check on the collar."),
    ("weekend-offender-zip-polo-navy", "Weekend Offender Check Zip Polo", "tops", "6900", "7900", 10,
     "Navy quarter-zip polo with a house-check collar and woven chest badge."),
    ("burberry-check-hood-zip-hoodie-black", "Burberry Check Hood Zip Hoodie – Black", "tops", "14500", None, 4,
     "Black cotton zip-up hoodie lined with the classic check inside the hood."),
    ("burberry-check-hood-zip-hoodie-grey", "Burberry Check Hood Zip Hoodie – Grey", "tops", "14500", None, 5,
     "Heather grey zip-up hoodie with an embroidered logo and check-lined hood."),
    ("vintage-wash-barrel-jeans", "Vintage Wash Barrel Jeans", "bottoms", "7900", None, 12,
     "Wide barrel-leg jeans in a faded vintage wash with curved knee seams."),
    ("levis-light-wash-straight-jeans", "Levi's Light Wash Straight Jeans", "bottoms", "7500", "8900", 9,
     "Straight, relaxed-fit jeans in a bleached light-blue wash."),
    ("levis-550-relaxed-jeans", "Levi's 550 Relaxed Fit Jeans", "bottoms", "7900", None, 8,
     "The classic relaxed-fit 550 in a mid-blue stonewash."),
    ("the-north-face-bucket-hat-black", "The North Face Bucket Hat", "hats", "3900", None, 15,
     "Black nylon bucket hat with a webbing band and adjustable chin cord."),
    ("weekend-offender-check-bucket-hat", "Weekend Offender Check Bucket Hat", "hats", "3500", None, 0,
     "Gingham-check bucket hat with a woven logo patch on the front."),
]


def seed() -> None:
    with SessionLocal() as db:
        if db.scalar(select(Product.id).limit(1)) is not None:
            sys.exit("The catalogue already has products; nothing was added.")
        db.add_all(
            Product(
                slug=slug, name=name, category=category, price=Decimal(price),
                compare_at_price=Decimal(old) if old else None, stock_quantity=stock,
                description=description, image_url=f"/{slug}.jpg",
            )
            for slug, name, category, price, old, stock, description in SAMPLE_PRODUCTS
        )
        db.commit()
    print(f"Added {len(SAMPLE_PRODUCTS)} sample products.")


def create_admin(email: str, name: str, role: str) -> None:
    """Creates an account, or resets an existing one's name, role and password.
    The password is typed in (hidden), never passed on the command line where it
    would be saved in the shell history."""
    password = getpass("Password (at least 10 characters): ")
    if password != getpass("Repeat password: "):
        sys.exit("Passwords don't match.")
    with SessionLocal() as db:
        try:
            admin, created = save_admin(db, email=email, full_name=name, password=password, role=role)
        except ValueError as error:
            sys.exit(str(error))
    print(f"{'Created' if created else 'Updated'} {admin.role} account {admin.email}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("seed", help="add the sample products to an empty catalogue")
    new_admin = commands.add_parser("create-admin", help="add an admin account, or reset its password")
    new_admin.add_argument("--email", required=True)
    new_admin.add_argument("--name", required=True)
    new_admin.add_argument("--role", choices=["admin", "staff"], default="admin")
    args = parser.parse_args()
    if args.command == "seed":
        seed()
    elif args.command == "create-admin":
        create_admin(args.email, args.name, args.role)


if __name__ == "__main__":
    main()
