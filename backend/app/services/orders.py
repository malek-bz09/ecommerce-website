"""Order business logic: checkout, stock, status changes, and the admin lists.

How stock works
---------------
- Placing an order takes its items out of stock straight away (they are reserved
  for that customer), so two customers can never be promised the same last item.
- Cancelling or returning an order puts its items back.
- Both happen inside one database transaction together with the order itself:
  either everything is saved, or nothing is.

How overselling is prevented
----------------------------
Before checking stock, the order locks the product rows it needs
(SELECT ... FOR UPDATE). A second order for the same product waits at that line
until the first one has committed, then sees the reduced stock. Products are
always locked in id order, so two orders can't each hold a lock the other needs
(a "deadlock").
"""

import re
import secrets
import uuid
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import distinct_on
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.algeria import WILAYA_BY_CODE
from app.core.config import get_settings
from app.core.errors import AppError
from app.models.order import ORDER_STATUSES, RESTOCKING_STATUSES, TRANSITIONS, Order
from app.models.order_item import OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate
from app.services.products import escape_like

# No 0/O or 1/I/L, so an order number read out on the phone can't be misheard
ORDER_NUMBER_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"


def cart_error(message: str) -> AppError:
    # cartChanged tells the checkout page to reload the products and show the cart again
    return AppError(409, message, cartChanged=True)


def new_order_number(db: Session) -> str:
    # 31^8 ≈ 850 billion possibilities: random, so they can't be guessed or counted
    while True:
        number = "ORD-" + "".join(secrets.choice(ORDER_NUMBER_ALPHABET) for _ in range(8))
        if db.scalar(select(Order.id).where(Order.order_number == number)) is None:
            return number


def find_by_idempotency_key(db: Session, key: str) -> Order | None:
    return db.scalar(select(Order).where(Order.idempotency_key == key))


def lock_products(db: Session, product_ids) -> dict[int, Product]:
    """Loads the products and locks their rows until this transaction ends."""
    rows = db.scalars(
        select(Product).where(Product.id.in_(product_ids)).order_by(Product.id).with_for_update()
    )
    return {product.id: product for product in rows}


def place_order(db: Session, data: OrderCreate, idempotency_key: str | None = None) -> tuple[Order, bool]:
    """Saves a new pending order and reserves its stock. Returns (order, created).

    created is False when this idempotency key was already used: the earlier order
    is returned instead of making a second one (e.g. a double-click on "Place order").
    """
    if idempotency_key and (existing := find_by_idempotency_key(db, idempotency_key)):
        return existing, False
    if not data.items:
        raise cart_error("Your cart is empty.")

    # The same product twice in the request counts as one line
    quantities: dict[int, int] = defaultdict(int)
    for item in data.items:
        quantities[item.id] += item.quantity

    products = lock_products(db, quantities)
    items = []
    for product_id, quantity in quantities.items():
        product = products.get(product_id)
        if product is None or not product.is_available:
            raise cart_error("An item in your cart is no longer available.")
        if product.stock_quantity == 0:
            raise cart_error(f"{product.name} is sold out. Please remove it from your cart.")
        if quantity > product.stock_quantity:
            raise cart_error(f"Only {product.stock_quantity} of {product.name} left in stock.")
        product.stock_quantity -= quantity  # safe: nobody else can change this row right now
        items.append(
            OrderItem(
                product_id=product.id, product_name=product.name, unit_price=product.price,
                quantity=quantity, subtotal=product.price * quantity,
            )
        )

    # Totals come only from database prices; Decimal keeps them exact
    subtotal = sum((item.subtotal for item in items), Decimal(0))
    delivery_fee = get_settings().delivery_fee
    customer = data.customer
    order = Order(
        order_number=new_order_number(db),
        customer_name=customer.full_name,
        customer_phone=customer.phone,
        customer_email=customer.email,
        wilaya_code=customer.wilaya,
        wilaya=WILAYA_BY_CODE[customer.wilaya],
        commune=customer.commune,
        shipping_address=customer.address,
        notes=customer.notes,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        total_amount=subtotal + delivery_fee,
        idempotency_key=idempotency_key,
        items=items,
    )
    db.add(order)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()  # also undoes the stock changes above
        # The same key sent twice at the same instant: the other request won, use its order
        if idempotency_key and (existing := find_by_idempotency_key(db, idempotency_key)):
            return existing, False
        raise exc
    db.refresh(order)
    return order, True


def get_order(db: Session, order_id: uuid.UUID, *, lock: bool = False) -> Order:
    query = select(Order).where(Order.id == order_id)
    order = db.scalar(query.with_for_update() if lock else query)
    if order is None:
        raise AppError(404, "Order not found.")
    return order


def change_status(db: Session, order_id: uuid.UUID, new_status: str) -> Order:
    # Lock the order: if two admins click "Cancel" at once, the second waits, then
    # sees "cancelled" and is refused, so the stock is only put back once
    order = get_order(db, order_id, lock=True)
    old_status = order.status
    if new_status not in TRANSITIONS[old_status]:
        raise AppError(409, f"A {old_status} order can't be marked {new_status}.")

    if new_status in RESTOCKING_STATUSES:
        # Put the items back (skipping products that were deleted since)
        products = lock_products(db, [i.product_id for i in order.items if i.product_id is not None])
        for item in order.items:
            if item.product_id in products:
                products[item.product_id].stock_quantity += item.quantity

    order.status = new_status
    setattr(order, f"{new_status}_at", func.now())  # e.g. shipped_at
    db.commit()
    db.refresh(order)
    return order


# ---------- Admin lists ----------


def shop_day_start(day: date) -> datetime:
    """Midnight at the start of `day` in the shop's time zone (orders are stored in UTC)."""
    return datetime.combine(day, time.min, tzinfo=ZoneInfo(get_settings().shop_timezone))


def search_orders(q: str | None, date_from: date | None, date_to: date | None) -> Select:
    query = select(Order)
    if q:
        pattern = f"%{escape_like(q.strip())}%"
        matches = [
            Order.order_number.ilike(pattern),
            Order.customer_name.ilike(pattern),
            Order.customer_email.ilike(pattern),
        ]
        # "0555 12 34" should find 0555123456
        digits = re.sub(r"\D", "", q)
        if digits:
            matches.append(Order.customer_phone.like(f"%{digits}%"))
        query = query.where(or_(*matches))
    if date_from:
        query = query.where(Order.created_at >= shop_day_start(date_from))
    if date_to:
        query = query.where(Order.created_at < shop_day_start(date_to + timedelta(days=1)))
    return query


def list_orders(
    db: Session, *, page: int, size: int, status: str | None = None, q: str | None = None,
    date_from: date | None = None, date_to: date | None = None,
) -> tuple[list[Order], int, dict[str, int]]:
    """One page of orders (newest first), the total, and the count for each status."""
    matching = search_orders(q, date_from, date_to)

    found = matching.subquery()
    counted = select(found.c.status, func.count()).group_by(found.c.status)
    status_counts = dict.fromkeys(ORDER_STATUSES, 0) | dict(db.execute(counted).all())

    if status:
        matching = matching.where(Order.status == status)
    total = db.scalar(select(func.count()).select_from(matching.subquery()))
    orders = db.scalars(
        matching.order_by(Order.created_at.desc(), Order.id).offset((page - 1) * size).limit(size)
    ).all()
    return list(orders), total, status_counts


def list_customers(db: Session, *, page: int, size: int, q: str | None = None) -> tuple[list[dict], int]:
    """Buyers, one per phone number, with their latest details and totals."""
    orders = select(Order)
    if q:
        pattern = f"%{escape_like(q.strip())}%"
        orders = orders.where(or_(Order.customer_name.ilike(pattern), Order.customer_phone.like(pattern)))
    orders = orders.subquery()

    totals = (
        select(
            orders.c.customer_phone.label("phone"),
            func.count().label("order_count"),
            # Money counts only once delivered, like revenue on the dashboard
            func.coalesce(func.sum(orders.c.total_amount).filter(orders.c.status == "delivered"), 0)
            .label("total_spent"),
            func.max(orders.c.created_at).label("last_order_at"),
        )
        .group_by(orders.c.customer_phone)
        .subquery()
    )
    # DISTINCT ON: for each phone, only the newest order (for the latest name and address)
    latest = (
        select(orders)
        .ext(distinct_on(orders.c.customer_phone))
        .order_by(orders.c.customer_phone, orders.c.created_at.desc())
        .subquery()
    )
    query = select(totals, latest).join(latest, latest.c.customer_phone == totals.c.phone)

    total = db.scalar(select(func.count()).select_from(totals))
    rows = db.execute(
        query.order_by(totals.c.last_order_at.desc(), totals.c.phone).offset((page - 1) * size).limit(size)
    ).mappings()
    customers = [
        {
            "id": row["phone"], "full_name": row["customer_name"], "phone": row["phone"],
            "email": row["customer_email"], "wilaya": row["wilaya"], "commune": row["commune"],
            "address": row["shipping_address"], "order_count": row["order_count"],
            "total_spent": row["total_spent"], "last_order_at": row["last_order_at"],
        }
        for row in rows
    ]
    return customers, total
