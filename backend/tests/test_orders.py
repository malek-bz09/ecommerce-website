"""Phase 5: checkout, stock, overselling, status changes, admin order lists, privacy."""

import re
import threading
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import func, select, update

from app.core.errors import AppError
from app.db.session import SessionLocal
from app.models.order import Order
from app.models.product import Product
from app.schemas.order import OrderCreate
from app.services import orders as service

ORDERS = "/api/v1/orders"
ADMIN_ORDERS = "/api/v1/admin/orders"


def add_product(name="Navy Polo", price="8500", stock=5, available=True) -> int:
    with SessionLocal() as db:
        product = Product(
            name=name, slug=name.lower().replace(" ", "-"), category="tops", price=Decimal(price),
            stock_quantity=stock, image_url="/p.jpg", is_available=available,
        )
        db.add(product)
        db.commit()
        return product.id


def stock_of(product_id: int) -> int:
    with SessionLocal() as db:
        return db.get(Product, product_id).stock_quantity


def order_count() -> int:
    with SessionLocal() as db:
        return db.scalar(select(func.count()).select_from(Order))


def checkout(items, **customer):
    return {
        "customer": {
            "fullName": "Amina Benali", "phone": "0555 12 34 56", "email": "amina@example.com",
            "wilaya": "16", "commune": "Hydra", "address": "12 rue des Oliviers, bât. B", "notes": "",
        } | customer,
        "items": [{"id": product_id, "quantity": quantity} for product_id, quantity in items],
    }


def place(client, items, key=None, **customer):
    headers = {"Idempotency-Key": key} if key else {}
    return client.post(ORDERS, json=checkout(items, **customer), headers=headers)


# ---------- Placing an order ----------


def test_order_is_saved_pending_with_server_side_totals(client):
    polo = add_product(price="8500.50", stock=5)
    hat = add_product(name="Bucket Hat", price="3900", stock=10)
    body = checkout([(polo, 2), (hat, 1)])
    # Prices and totals sent by the browser are ignored
    body["items"][0]["price"] = 1
    body["total"] = 1

    response = client.post(ORDERS, json=body)
    assert response.status_code == 201, response.text
    order = response.json()
    assert re.fullmatch(r"ORD-[2-9A-HJ-NP-Z]{8}", order["orderNumber"])
    assert order["status"] == "pending"
    assert order["paymentMethod"] == "cod"
    assert order["lines"] == [
        {"id": polo, "name": "Navy Polo", "price": 8500.5, "quantity": 2, "subtotal": 17001.0},
        {"id": hat, "name": "Bucket Hat", "price": 3900.0, "quantity": 1, "subtotal": 3900.0},
    ]
    assert (order["subtotal"], order["deliveryFee"], order["total"]) == (20901.0, 600.0, 21501.0)
    assert order["customer"]["phone"] == "0555123456"  # normalised
    assert order["customer"]["wilaya"] == "Alger"  # the name, from code "16"
    # Stock is reserved straight away
    assert (stock_of(polo), stock_of(hat)) == (3, 9)


def test_same_product_twice_becomes_one_line(client):
    polo = add_product(stock=5)
    lines = place(client, [(polo, 1), (polo, 2)]).json()["lines"]
    assert [(line["id"], line["quantity"]) for line in lines] == [(polo, 3)]


def test_order_response_has_no_internal_fields(client):
    order = place(client, [(add_product(), 1)], key="checkout-1234").json()
    assert "id" not in order and "idempotencyKey" not in order


def test_email_is_optional(client):
    order = place(client, [(add_product(), 1)], email="").json()
    assert order["customer"]["email"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fullName", "Amina"),  # first name only
        ("fullName", "R2-D2 Droid"),
        ("phone", "0123456789"),  # not a mobile number
        ("phone", "055512345"),
        ("email", "not-an-email"),
        ("wilaya", "99"),
        ("commune", "H"),
        ("address", "short"),
        ("notes", "x" * 501),
    ],
)
def test_invalid_customer_details_are_reported_by_field(client, field, value):
    response = place(client, [(add_product(), 1)], **{field: value})
    assert response.status_code == 422
    assert field in response.json()["detail"]["fieldErrors"]
    assert order_count() == 0


@pytest.mark.parametrize("quantity", [0, -1, 101])
def test_invalid_quantity(client, quantity):
    assert place(client, [(add_product(), quantity)]).status_code == 422


# ---------- Stock problems ----------


def cart_error(response, status=409):
    assert response.status_code == status
    detail = response.json()["detail"]
    assert detail["cartChanged"] is True
    return detail["message"]


def test_empty_cart(client):
    assert cart_error(place(client, [])) == "Your cart is empty."


def test_more_than_in_stock(client):
    polo = add_product(stock=2)
    assert cart_error(place(client, [(polo, 3)])) == "Only 2 of Navy Polo left in stock."
    assert stock_of(polo) == 2


def test_sold_out(client):
    assert "sold out" in cart_error(place(client, [(add_product(stock=0), 1)]))


@pytest.mark.parametrize("product", ["missing", "hidden"])
def test_unavailable_product(client, product):
    product_id = 999 if product == "missing" else add_product(available=False)
    assert cart_error(place(client, [(product_id, 1)])) == "An item in your cart is no longer available."


def test_one_bad_line_saves_nothing(client):
    # The first line is fine, the second isn't: the first line's stock must not change
    polo = add_product(stock=5)
    hat = add_product(name="Bucket Hat", stock=1)
    cart_error(place(client, [(polo, 2), (hat, 5)]))
    assert stock_of(polo) == 5
    assert order_count() == 0


# ---------- Overselling ----------


def place_at_the_same_time(product_id: int, buyers: int) -> list[bool]:
    """`buyers` people order 1 of the product at the same instant, each with their own
    database connection, like separate web requests. Returns who succeeded."""
    start = threading.Barrier(buyers)
    results = []

    def buy():
        data = OrderCreate.model_validate(checkout([(product_id, 1)]))
        with SessionLocal() as db:
            start.wait()  # everyone goes at once
            try:
                service.place_order(db, data)
                results.append(True)
            except AppError:
                results.append(False)

    threads = [threading.Thread(target=buy) for _ in range(buyers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_last_item_is_sold_only_once():
    polo = add_product(stock=1)
    results = place_at_the_same_time(polo, buyers=8)
    assert results.count(True) == 1
    assert stock_of(polo) == 0
    assert order_count() == 1


def test_stock_is_never_oversold():
    polo = add_product(stock=5)
    results = place_at_the_same_time(polo, buyers=12)
    assert results.count(True) == 5
    assert stock_of(polo) == 0


# ---------- Duplicate submissions ----------


def test_same_idempotency_key_returns_the_same_order(client):
    polo = add_product(stock=5)
    first = place(client, [(polo, 2)], key="checkout-abc-123")
    again = place(client, [(polo, 2)], key="checkout-abc-123")
    assert (first.status_code, again.status_code) == (201, 200)
    assert first.json()["orderNumber"] == again.json()["orderNumber"]
    assert stock_of(polo) == 3  # taken once
    assert order_count() == 1


def test_bad_idempotency_key_is_rejected(client):
    assert place(client, [(add_product(), 1)], key="x").status_code == 422


def test_order_submissions_are_rate_limited(client):
    polo = add_product(stock=50)
    for _ in range(10):
        assert place(client, [(polo, 1)]).status_code == 201
    assert place(client, [(polo, 1)]).status_code == 429


# ---------- Snapshots ----------


def test_order_keeps_name_and_price_when_product_changes(client, admin_client):
    polo = add_product(price="8500", stock=5)
    place(client, [(polo, 1)])
    admin_client.patch(f"/api/v1/products/{polo}", json={"name": "Renamed", "price": 9999})
    order_id = admin_client.get(ADMIN_ORDERS).json()["items"][0]["id"]
    line = admin_client.get(f"{ADMIN_ORDERS}/{order_id}").json()["lines"][0]
    assert (line["name"], line["price"]) == ("Navy Polo", 8500)


def test_order_survives_product_deletion(client, admin_client):
    polo = add_product(stock=5)
    place(client, [(polo, 1)])
    assert admin_client.delete(f"/api/v1/products/{polo}").status_code == 204
    order_id = admin_client.get(ADMIN_ORDERS).json()["items"][0]["id"]
    order = admin_client.get(f"{ADMIN_ORDERS}/{order_id}").json()
    assert order["lines"][0] | {"id": None, "slug": None, "image": None} == order["lines"][0]
    assert order["lines"][0]["name"] == "Navy Polo"
    # Cancelling still works; there's just no product to put the stock back on
    assert admin_client.patch(f"{ADMIN_ORDERS}/{order_id}/status", json={"status": "cancelled"}).status_code == 200


# ---------- Status changes ----------


@pytest.fixture
def order(client, admin_client):
    """A pending order for 2 of a product that had 5 in stock. Returns (order id, product id)."""
    polo = add_product(stock=5)
    place(client, [(polo, 2)])
    return admin_client.get(ADMIN_ORDERS).json()["items"][0]["id"], polo


def set_status(client, order_id, status):
    return client.patch(f"{ADMIN_ORDERS}/{order_id}/status", json={"status": status})


def test_full_journey_to_delivered(admin_client, order):
    order_id, polo = order
    for status in ["confirmed", "processing", "shipped", "delivered"]:
        response = set_status(admin_client, order_id, status)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status
    detail = response.json()
    assert detail["nextStatuses"] == ["returned"]
    assert all(detail["history"][s] for s in ["pending", "confirmed", "processing", "shipped", "delivered"])
    assert detail["history"]["cancelled"] is None
    assert stock_of(polo) == 3  # delivered items stay sold


@pytest.mark.parametrize(
    ("path", "refused"),
    [
        ([], "shipped"),  # pending can't skip ahead
        ([], "delivered"),
        (["confirmed"], "pending"),  # no going back
        (["confirmed", "processing", "shipped"], "cancelled"),  # already on the road: use returned
        (["cancelled"], "confirmed"),  # final
    ],
)
def test_forbidden_transitions(admin_client, order, path, refused):
    order_id, _ = order
    for status in path:
        assert set_status(admin_client, order_id, status).status_code == 200
    response = set_status(admin_client, order_id, refused)
    assert response.status_code == 409
    assert "can't be marked" in response.json()["detail"]["message"]


def test_unknown_status_is_rejected(admin_client, order):
    assert set_status(admin_client, order[0], "lost").status_code == 422


@pytest.mark.parametrize(
    "path", [["cancelled"], ["confirmed", "processing", "cancelled"],
             ["confirmed", "processing", "shipped", "returned"],
             ["confirmed", "processing", "shipped", "delivered", "returned"]]
)
def test_cancelled_and_returned_orders_put_stock_back(admin_client, order, path):
    order_id, polo = order
    assert stock_of(polo) == 3
    for status in path:
        set_status(admin_client, order_id, status)
    assert stock_of(polo) == 5


def test_cancelling_twice_restocks_once(admin_client, order):
    order_id, polo = order
    assert set_status(admin_client, order_id, "cancelled").status_code == 200
    assert set_status(admin_client, order_id, "cancelled").status_code == 409
    assert stock_of(polo) == 5


def test_two_admins_cancelling_at_once_restock_once(admin_client, order):
    order_id, polo = order
    start = threading.Barrier(2)
    codes = []

    def cancel():
        start.wait()
        codes.append(set_status(admin_client, order_id, "cancelled").status_code)

    threads = [threading.Thread(target=cancel) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(codes) == [200, 409]
    assert stock_of(polo) == 5


def test_staff_can_manage_orders(staff_client, order):
    assert set_status(staff_client, order[0], "confirmed").status_code == 200


def test_missing_order(admin_client):
    missing = "00000000-0000-0000-0000-000000000000"
    assert admin_client.get(f"{ADMIN_ORDERS}/{missing}").status_code == 404
    assert set_status(admin_client, missing, "confirmed").status_code == 404
    assert admin_client.get(f"{ADMIN_ORDERS}/not-a-uuid").status_code == 422


# ---------- Admin list: search, filters, pagination ----------


@pytest.fixture
def three_orders(client, admin_client):
    polo = add_product(stock=50)
    place(client, [(polo, 1)], fullName="Amina Benali", phone="0555111111")
    place(client, [(polo, 2)], fullName="Karim Saidi", phone="0666222222", email="karim@example.com")
    place(client, [(polo, 3)], fullName="Amina Benali", phone="0555111111")
    orders = admin_client.get(ADMIN_ORDERS).json()["items"]
    set_status(admin_client, orders[0]["id"], "confirmed")
    return orders


def test_list_newest_first_with_counts(admin_client, three_orders):
    page = admin_client.get(ADMIN_ORDERS).json()
    assert page["total"] == 3
    assert [o["itemCount"] for o in page["items"]] == [3, 2, 1]
    assert page["statusCounts"] == {
        "pending": 2, "confirmed": 1, "processing": 0, "shipped": 0, "delivered": 0,
        "cancelled": 0, "returned": 0,
    }


def test_filter_by_status_keeps_all_counts(admin_client, three_orders):
    page = admin_client.get(ADMIN_ORDERS, params={"status": "pending"}).json()
    assert page["total"] == 2
    assert page["statusCounts"]["confirmed"] == 1  # the tabs still show every count


@pytest.mark.parametrize(
    ("q", "expected"),
    [("karim", 1), ("AMINA", 2), ("0555 11", 2), ("karim@example", 1), ("nobody", 0)],
)
def test_search(admin_client, three_orders, q, expected):
    assert admin_client.get(ADMIN_ORDERS, params={"q": q}).json()["total"] == expected


def test_search_by_order_number(admin_client, three_orders):
    number = three_orders[1]["orderNumber"]
    items = admin_client.get(ADMIN_ORDERS, params={"q": number.lower()}).json()["items"]
    assert [o["orderNumber"] for o in items] == [number]


def test_date_filter_uses_shop_days(admin_client, three_orders):
    # 23:30 UTC on 1 March is already 00:30 on 2 March in Algiers (UTC+1)
    with SessionLocal() as db:
        db.execute(update(Order).values(created_at=datetime(2026, 3, 1, 23, 30, tzinfo=UTC)))
        db.commit()
    count = lambda **p: admin_client.get(ADMIN_ORDERS, params=p).json()["total"]  # noqa: E731
    assert count(dateFrom="2026-03-02", dateTo="2026-03-02") == 3
    assert count(dateTo="2026-03-01") == 0
    assert count(dateFrom="2026-03-03") == 0


def test_pagination(admin_client, three_orders):
    page = admin_client.get(ADMIN_ORDERS, params={"size": 2, "page": 2}).json()
    assert (page["pages"], len(page["items"])) == (2, 1)


def test_customers_are_grouped_by_phone(admin_client, three_orders):
    order_id = admin_client.get(ADMIN_ORDERS, params={"q": "karim"}).json()["items"][0]["id"]
    for status in ["confirmed", "processing", "shipped", "delivered"]:
        set_status(admin_client, order_id, status)
    customers = admin_client.get("/api/v1/admin/customers").json()
    assert customers["total"] == 2
    by_phone = {c["phone"]: c for c in customers["items"]}
    assert by_phone["0555111111"]["orderCount"] == 2
    assert by_phone["0555111111"]["totalSpent"] == 0  # nothing delivered yet
    assert by_phone["0666222222"]["totalSpent"] == 2 * 8500 + 600


# ---------- Customer data protection ----------


@pytest.mark.parametrize(
    ("method", "url"),
    [
        ("get", ADMIN_ORDERS),
        ("get", f"{ADMIN_ORDERS}/00000000-0000-0000-0000-000000000000"),
        ("patch", f"{ADMIN_ORDERS}/00000000-0000-0000-0000-000000000000/status"),
        ("get", "/api/v1/admin/customers"),
    ],
)
def test_public_cannot_read_orders_or_customers(client, method, url):
    assert getattr(client, method)(url).status_code == 401


def test_there_is_no_public_order_lookup(client):
    order = place(client, [(add_product(), 1)]).json()
    assert client.get(f"{ORDERS}/{order['orderNumber']}").status_code in (404, 405)
    assert client.get(ORDERS).status_code == 405
