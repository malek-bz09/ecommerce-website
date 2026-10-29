"""The admin dashboard numbers."""

from tests.test_orders import add_product, place

STATS = "/api/v1/admin/stats"


def move(admin_client, order_id, *statuses):
    for status in statuses:
        assert admin_client.patch(f"/api/v1/admin/orders/{order_id}/status", json={"status": status}).status_code == 200


def test_empty_shop(admin_client):
    stats = admin_client.get(STATS).json()
    assert stats["revenue"] == 0
    assert stats["returnRate"] is None
    assert stats["customers"] == 0
    assert set(stats["statusCounts"].values()) == {0}
    assert len(stats["ordersPerDay"]) == 14
    assert stats["recentOrders"] == stats["topProducts"] == stats["lowStock"] == []


def test_numbers_follow_the_orders(client, admin_client):
    polo = add_product("Navy Polo", price="1000", stock=10)
    hat = add_product("Bucket Hat", price="500", stock=2)
    delivered = place(client, [(polo, 2)]).json()
    returned = place(client, [(polo, 1)], phone="0661 11 22 33").json()
    place(client, [(hat, 1)])  # stays pending

    orders = {o["orderNumber"]: o["id"] for o in admin_client.get("/api/v1/admin/orders").json()["items"]}
    move(admin_client, orders[delivered["orderNumber"]], "confirmed", "processing", "shipped", "delivered")
    move(admin_client, orders[returned["orderNumber"]], "confirmed", "processing", "shipped", "returned")

    stats = admin_client.get(STATS).json()
    assert stats["revenue"] == 2600  # 2 × 1000 + 600 delivery
    assert stats["averageOrder"] == 2600
    assert stats["awaitingPayment"] == 0
    assert stats["returnRate"] == 0.5
    assert stats["customers"] == 2
    assert stats["statusCounts"]["pending"] == 1
    assert stats["ordersPerDay"][-1]["orders"] == 3
    assert [(p["name"], p["sold"]) for p in stats["topProducts"]] == [("Navy Polo", 2), ("Bucket Hat", 1)]
    assert [(p["name"], p["stock"]) for p in stats["lowStock"]] == [("Bucket Hat", 1)]
    assert len(stats["recentOrders"]) == 3


def test_staff_can_see_stats_but_the_public_cannot(client, staff_client):
    assert staff_client.get(STATS).status_code == 200
    assert client.get(STATS).status_code == 401
