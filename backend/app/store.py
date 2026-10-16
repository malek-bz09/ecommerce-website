"""Public endpoints used by the storefront."""

import secrets
import sqlite3

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from .checkout import WILAYA_BY_CODE, normalize_phone, validate_customer
from .database import get_db
from .security import now

router = APIRouter(prefix="/api")

DELIVERY_FEE = 600  # keep in sync with DELIVERY_FEE in src/services/orders.js


class CustomerIn(BaseModel):
    fullName: str
    phone: str
    email: str
    wilaya: str
    commune: str
    address: str
    notes: str = ""


class ItemIn(BaseModel):
    id: int
    quantity: int


class OrderIn(BaseModel):
    customer: CustomerIn
    items: list[ItemIn]


def order_error(status: int, message: str, **extra):
    # Every error has a "message" the shop can show as-is
    return HTTPException(status, detail={"message": message, **extra})


@router.post("/orders", status_code=201)
def place_order(order: OrderIn, db: sqlite3.Connection = Depends(get_db)):
    c = order.customer.model_dump()
    field_errors = validate_customer(c)
    if field_errors:
        raise order_error(422, "Some of your details are invalid.", fieldErrors=field_errors)

    if not order.items:
        raise order_error(409, "Your cart is empty.", cartChanged=True)

    # Prices and names come from the database, never from the browser
    lines = []
    for item in order.items:
        product = db.execute("SELECT * FROM products WHERE id = ? AND deleted = 0", (item.id,)).fetchone()
        if not product:
            raise order_error(409, "An item in your cart is no longer available.", cartChanged=True)
        if item.quantity < 1:
            raise order_error(409, f"Invalid quantity for {product['name']}.", cartChanged=True)
        if product["stock"] == 0:
            raise order_error(409, f"{product['name']} is sold out. Please remove it from your cart.", cartChanged=True)
        if item.quantity > product["stock"]:
            raise order_error(409, f"Only {product['stock']} of {product['name']} left in stock.", cartChanged=True)
        lines.append({"id": product["id"], "name": product["name"], "price": product["price"], "quantity": item.quantity})

    customer = {
        "fullName": c["fullName"].strip(),
        "phone": normalize_phone(c["phone"]),
        "email": c["email"].strip().lower(),
        "wilaya": WILAYA_BY_CODE[c["wilaya"]],
        "commune": c["commune"].strip(),
        "address": c["address"].strip(),
        "notes": c["notes"].strip(),
    }
    subtotal = sum(line["price"] * line["quantity"] for line in lines)
    order_id = f"ORD-{secrets.token_hex(4).upper()}"

    # The order waits as "pending" until an admin confirms the sale.
    # Stock only goes down at that point.
    with db:
        db.execute(
            """INSERT INTO orders (id, created_at, full_name, phone, email, wilaya, commune,
                                   address, notes, subtotal, delivery_fee, total)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (order_id, now(), *customer.values(), subtotal, DELIVERY_FEE, subtotal + DELIVERY_FEE),
        )
        db.executemany(
            "INSERT INTO order_items (order_id, product_id, name, price, quantity) VALUES (?, ?, ?, ?, ?)",
            [(order_id, l["id"], l["name"], l["price"], l["quantity"]) for l in lines],
        )

    # Same shape the order confirmation page already uses
    return {
        "id": order_id,
        "paymentMethod": "cod",
        "customer": customer,
        "lines": lines,
        "subtotal": subtotal,
        "deliveryFee": DELIVERY_FEE,
        "total": subtotal + DELIVERY_FEE,
    }
