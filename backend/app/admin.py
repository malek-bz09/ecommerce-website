"""Admin endpoints. Everything except /login needs a valid session token."""

import psycopg
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from .database import get_db
from .security import DUMMY_HASH, new_session, now, verify_password

router = APIRouter(prefix="/api/admin")


def error(status: int, message: str):
    return HTTPException(status, detail={"message": message})


def require_admin(authorization: str = Header(default=""), db: psycopg.Connection = Depends(get_db)):
    """Dependency: reads "Authorization: Bearer <token>" and returns the admin, or 401."""
    token = authorization.removeprefix("Bearer ").strip()
    admin = db.execute(
        """SELECT admins.username, admins.name FROM sessions
           JOIN admins ON admins.username = sessions.username
           WHERE sessions.token = %s AND sessions.expires_at > %s""",
        (token, now()),
    ).fetchone()
    if not admin:
        raise error(401, "Your session has expired. Please sign in again.")
    return {"username": admin["username"], "name": admin["name"], "token": token}


class LoginIn(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(body: LoginIn, db: psycopg.Connection = Depends(get_db)):
    admin = db.execute("SELECT * FROM admins WHERE username = %s", (body.username.strip(),)).fetchone()
    password_ok = verify_password(body.password, admin["password_hash"] if admin else DUMMY_HASH)
    if not admin or not password_ok:
        raise error(401, "Incorrect username or password.")
    token = new_session(db, admin["username"])
    return {"token": token, "user": {"username": admin["username"], "name": admin["name"]}}


@router.post("/logout", status_code=204)
def logout(admin=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    with db.transaction():
        db.execute("DELETE FROM sessions WHERE token = %s", (admin["token"],))


# What each status can change to. Anything else is refused.
#   pending   → confirmed (sale accepted: stock goes down, buyer becomes a customer)
#             → cancelled
#   confirmed → delivered (customer paid)  → returned (sent back: stock goes up again)
#             → returned (refused at the door)
#             → cancelled (stock goes up again)
TRANSITIONS = {
    "pending": ("confirmed", "cancelled"),
    "confirmed": ("delivered", "returned", "cancelled"),
    "delivered": ("returned",),
    "returned": (),
    "cancelled": (),
}


def customer_json(o) -> dict:
    return {
        "fullName": o["full_name"], "phone": o["phone"], "email": o["email"],
        "wilaya": o["wilaya"], "commune": o["commune"], "address": o["address"],
        "notes": o["notes"],
    }


@router.get("/orders")
def list_orders(_=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    # Pending first (they need action), then newest first
    orders = db.execute(
        "SELECT * FROM orders ORDER BY status = 'pending' DESC, created_at DESC"
    ).fetchall()
    counts = {
        r["order_id"]: r["count"]
        for r in db.execute("SELECT order_id, SUM(quantity) AS count FROM order_items GROUP BY order_id")
    }
    return [
        {
            "id": o["id"],
            "status": o["status"],
            "createdAt": o["created_at"],
            "customer": customer_json(o),
            "itemCount": counts.get(o["id"], 0),
            "total": o["total"],
        }
        for o in orders
    ]


def find_order(db, order_id: str):
    order = db.execute("SELECT * FROM orders WHERE id = %s", (order_id,)).fetchone()
    if not order:
        raise error(404, "Order not found.")
    return order


@router.get("/orders/{order_id}")
def get_order(order_id: str, _=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    o = find_order(db, order_id)
    items = db.execute(
        """SELECT order_items.*, products.image, products.slug, products.deleted
           FROM order_items JOIN products ON products.id = order_items.product_id
           WHERE order_id = %s""",
        (order_id,),
    ).fetchall()
    return {
        "id": o["id"],
        "status": o["status"],
        "nextStatuses": TRANSITIONS[o["status"]],
        "history": {  # when each step happened (null = not yet)
            "pending": o["created_at"], "confirmed": o["confirmed_at"],
            "delivered": o["delivered_at"], "returned": o["returned_at"],
            "cancelled": o["cancelled_at"],
        },
        "customer": customer_json(o),
        "lines": [
            {"id": i["product_id"], "name": i["name"], "price": i["price"], "quantity": i["quantity"],
             "image": i["image"], "slug": None if i["deleted"] else i["slug"]}
            for i in items
        ],
        "subtotal": o["subtotal"],
        "deliveryFee": o["delivery_fee"],
        "total": o["total"],
    }


class StatusIn(BaseModel):
    status: str


@router.post("/orders/{order_id}/status")
def change_status(order_id: str, body: StatusIn, _=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    order = find_order(db, order_id)
    old, new = order["status"], body.status
    if new not in TRANSITIONS[old]:
        raise error(409, f"A {old} order can't be marked {new}.")
    items = db.execute("SELECT * FROM order_items WHERE order_id = %s", (order_id,)).fetchall()

    # "with db" is a transaction: if anything inside fails, every change is undone
    with db.transaction():
        if new == "confirmed":
            for item in items:
                # Only subtract when there is enough left, in one step, so two admins
                # confirming at the same time can't sell the same last item twice
                updated = db.execute(
                    "UPDATE products SET stock = stock - %s WHERE id = %s AND stock >= %s",
                    (item["quantity"], item["product_id"], item["quantity"]),
                )
                if updated.rowcount == 0:
                    raise error(409, f"Not enough stock left for {item['name']}.")
            add_customer(db, order)

        # Stock was taken when the order was confirmed; put it back
        if old in ("confirmed", "delivered") and new in ("returned", "cancelled"):
            db.cursor().executemany(
                "UPDATE products SET stock = stock + %s WHERE id = %s",
                [(item["quantity"], item["product_id"]) for item in items],
            )

        # new is one of our known statuses (checked above), so it's safe in the column name
        db.execute(f"UPDATE orders SET status = %s, {new}_at = %s WHERE id = %s", (new, now(), order_id))
    return get_order(order_id, None, db)


def add_customer(db, order) -> None:
    # One customer per phone number; their details are updated to the latest order
    db.execute(
        """INSERT INTO customers (full_name, phone, email, wilaya, commune, address, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s)
           ON CONFLICT (phone) DO UPDATE SET
               full_name = excluded.full_name, email = excluded.email,
               wilaya = excluded.wilaya, commune = excluded.commune,
               address = excluded.address""",
        (order["full_name"], order["phone"], order["email"], order["wilaya"],
         order["commune"], order["address"], now()),
    )
    customer_id = db.execute("SELECT id FROM customers WHERE phone = %s", (order["phone"],)).fetchone()["id"]
    db.execute("UPDATE orders SET customer_id = %s WHERE id = %s", (customer_id, order["id"]))


@router.get("/customers")
def list_customers(_=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    # Money counts only for orders that weren't returned or cancelled
    rows = db.execute(
        """SELECT customers.*, COUNT(orders.id) AS order_count,
                  SUM(CASE WHEN orders.status IN ('confirmed', 'delivered') THEN orders.total ELSE 0 END)
                      AS total_spent,
                  MAX(orders.created_at) AS last_order_at
           FROM customers
           JOIN orders ON orders.customer_id = customers.id
           GROUP BY customers.id
           ORDER BY last_order_at DESC"""
    )
    return [
        {
            "id": r["id"], "fullName": r["full_name"], "phone": r["phone"], "email": r["email"],
            "wilaya": r["wilaya"], "commune": r["commune"], "address": r["address"],
            "orderCount": r["order_count"], "totalSpent": r["total_spent"],
            "lastOrderAt": r["last_order_at"],
        }
        for r in rows
    ]


LOW_STOCK = 3
CHART_DAYS = 14


@router.get("/stats")
def stats(_=Depends(require_admin), db: psycopg.Connection = Depends(get_db)):
    def one(sql):  # runs a query that returns a single number
        return db.execute(sql).fetchone()["n"]

    counts = dict.fromkeys(TRANSITIONS, 0) | {
        r["status"]: r["count"] for r in db.execute("SELECT status, COUNT(*) AS count FROM orders GROUP BY status")
    }
    finished = counts["delivered"] + counts["returned"]

    # Orders placed per day for the last 14 days, including days with none
    today = datetime.now(UTC).date()  # orders are stored in UTC
    days = [(today - timedelta(days=n)).isoformat() for n in range(CHART_DAYS - 1, -1, -1)]
    placed = {
        r["day"]: r["count"]
        for r in db.execute(
            """SELECT substr(created_at, 1, 10) AS day, COUNT(*) AS count FROM orders
               WHERE substr(created_at, 1, 10) >= %s GROUP BY day""",
            (days[0],),
        )
    }

    return {
        # Cash on delivery: money is in hand only once an order is delivered
        "revenue": one("SELECT COALESCE(SUM(total), 0) AS n FROM orders WHERE status = 'delivered'"),
        "awaitingPayment": one("SELECT COALESCE(SUM(total), 0) AS n FROM orders WHERE status = 'confirmed'"),
        "averageOrder": one("SELECT COALESCE(ROUND(AVG(total))::int, 0) AS n FROM orders WHERE status = 'delivered'"),
        "returnRate": counts["returned"] / finished if finished else None,
        "customers": one("SELECT COUNT(*) AS n FROM customers"),
        "statusCounts": counts,
        "ordersPerDay": [{"date": d, "orders": placed.get(d, 0)} for d in days],
        "topProducts": [
            dict(r) for r in db.execute(
                """SELECT products.id, products.name, products.image, SUM(order_items.quantity) AS sold
                   FROM order_items
                   JOIN orders ON orders.id = order_items.order_id
                   JOIN products ON products.id = order_items.product_id
                   WHERE orders.status IN ('confirmed', 'delivered')
                   GROUP BY products.id ORDER BY sold DESC LIMIT 5"""
            )
        ],
        "lowStock": [
            dict(r) for r in db.execute(
                "SELECT id, name, image, stock FROM products WHERE deleted = 0 AND stock <= %s ORDER BY stock",
                (LOW_STOCK,),
            )
        ],
        "recentOrders": [
            {"id": r["id"], "fullName": r["full_name"], "total": r["total"],
             "status": r["status"], "createdAt": r["created_at"]}
            for r in db.execute("SELECT * FROM orders ORDER BY created_at DESC LIMIT 5")
        ],
    }
