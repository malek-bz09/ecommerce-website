"""Phase 3: products: create, read, update, delete, list, search, filter, validation."""

import pytest

URL = "/api/v1/products"
ADMIN_URL = "/api/v1/admin/products"


def product_data(**overrides):
    data = {
        "name": "Check Collar Polo",
        "description": "Navy cotton polo.",
        "category": "tops",
        "price": 8500,
        "stock": 6,
        "imageUrl": "/polo.jpg",
    }
    return data | overrides


@pytest.fixture
def client(admin_client):
    # Every request in this file is made by a signed-in admin. Who may do what is
    # tested in test_auth.py; hidden-product tests still use the public URLs.
    return admin_client


@pytest.fixture
def make_product(client):
    def make(**overrides):
        response = client.post(URL, json=product_data(**overrides))
        assert response.status_code == 201, response.text
        return response.json()

    return make


# ---------- Create ----------


def test_create_returns_the_full_product(client):
    response = client.post(URL, json=product_data(compareAtPrice="9900.50"))
    assert response.status_code == 201
    product = response.json()
    assert product["id"] > 0
    assert product["slug"] == "check-collar-polo"
    assert product["price"] == 8500  # a JSON number, not the string "8500.00"
    assert product["compareAtPrice"] == 9900.5
    assert product["stock"] == 6
    assert product["images"] == ["/polo.jpg"]
    assert product["isAvailable"] is True
    assert product["createdAt"] and product["updatedAt"]


def test_same_name_gets_a_different_slug(make_product):
    assert make_product()["slug"] == "check-collar-polo"
    assert make_product()["slug"] == "check-collar-polo-2"
    assert make_product()["slug"] == "check-collar-polo-3"


def test_slug_drops_accents_and_punctuation(make_product):
    assert make_product(name="Levi's Café Jeans – Blue!")["slug"] == "levis-cafe-jeans-blue"


def test_text_is_trimmed(make_product):
    assert make_product(name="  Polo  ")["name"] == "Polo"


# ---------- Invalid input ----------


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("name", ""),
        ("name", "x"),
        ("name", "x" * 121),
        ("category", "shoes"),
        ("price", 0),
        ("price", -5),
        ("price", "12.345"),  # more than 2 decimals
        ("price", "abc"),
        ("stock", -1),
        ("stock", 1.5),
        ("imageUrl", "javascript:alert(1)"),
        ("description", "x" * 2001),
    ],
)
def test_invalid_field_is_reported_by_name(client, field, value):
    response = client.post(URL, json=product_data(**{field: value}))
    assert response.status_code == 422
    assert field in response.json()["detail"]["fieldErrors"]


def test_missing_required_fields_are_all_reported(client):
    response = client.post(URL, json={})
    assert response.status_code == 422
    assert set(response.json()["detail"]["fieldErrors"]) == {"name", "category", "price", "stock", "imageUrl"}


def test_old_price_must_be_above_price(client):
    response = client.post(URL, json=product_data(price=8500, compareAtPrice=8000))
    assert response.status_code == 422
    assert "compareAtPrice" in response.json()["detail"]["fieldErrors"]


# ---------- Read ----------


def test_get_by_id_and_by_slug(client, make_product):
    product = make_product()
    by_id = client.get(f"{URL}/{product['id']}")
    by_slug = client.get(f"{URL}/by-slug/{product['slug']}")
    assert by_id.status_code == by_slug.status_code == 200
    assert by_id.json() == by_slug.json()


def test_public_product_hides_admin_fields(client, make_product):
    public = client.get(f"{URL}/{make_product()['id']}").json()
    assert set(public) == {
        "id", "slug", "name", "description", "category", "price", "compareAtPrice", "stock", "images"
    }


def test_missing_product_is_404(client):
    assert client.get(f"{URL}/999").json() == {"detail": {"message": "Product not found."}}
    assert client.get(f"{URL}/999").status_code == 404
    assert client.get(f"{URL}/by-slug/nope").status_code == 404
    assert client.patch(f"{URL}/999", json={"name": "New"}).status_code == 404
    assert client.delete(f"{URL}/999").status_code == 404


def test_non_numeric_id_is_rejected(client):
    assert client.get(f"{URL}/abc").status_code == 422


# ---------- Hidden products ----------


def test_hidden_product_is_invisible_in_the_shop_but_not_to_admins(client, make_product):
    hidden = make_product(isAvailable=False)
    assert client.get(f"{URL}/{hidden['id']}").status_code == 404
    assert client.get(f"{URL}/by-slug/{hidden['slug']}").status_code == 404
    assert client.get(URL).json()["total"] == 0
    assert client.get(f"{ADMIN_URL}/{hidden['id']}").status_code == 200
    assert client.get(ADMIN_URL).json()["total"] == 1


# ---------- Update ----------


def test_patch_changes_only_the_fields_sent(client, make_product):
    product = make_product()
    response = client.patch(f"{URL}/{product['id']}", json={"price": 7000, "stock": 2})
    assert response.status_code == 200
    updated = response.json()
    assert (updated["price"], updated["stock"]) == (7000, 2)
    assert updated["name"] == product["name"]
    assert updated["updatedAt"] > product["updatedAt"]


def test_renaming_keeps_the_slug(client, make_product):
    product = make_product()
    updated = client.patch(f"{URL}/{product['id']}", json={"name": "Brand New Name"}).json()
    assert updated["name"] == "Brand New Name"
    assert updated["slug"] == product["slug"]


def test_null_removes_old_price_but_is_refused_for_required_fields(client, make_product):
    product = make_product(compareAtPrice=9900)
    cleared = client.patch(f"{URL}/{product['id']}", json={"compareAtPrice": None})
    assert cleared.json()["compareAtPrice"] is None
    refused = client.patch(f"{URL}/{product['id']}", json={"price": None})
    assert refused.status_code == 422
    assert "price" in refused.json()["detail"]["fieldErrors"]


def test_price_rule_checks_the_combined_result(client, make_product):
    # Old price 9000 is fine with price 8500, but not once the price rises to 9500
    product = make_product(price=8500, compareAtPrice=9000)
    response = client.patch(f"{URL}/{product['id']}", json={"price": 9500})
    assert response.status_code == 422
    assert client.get(f"{URL}/{product['id']}").json()["price"] == 8500  # unchanged


# ---------- Delete ----------


def test_delete(client, make_product):
    product = make_product()
    assert client.delete(f"{URL}/{product['id']}").status_code == 204
    assert client.get(f"{URL}/{product['id']}").status_code == 404


# ---------- List, search, filter, pagination ----------


@pytest.fixture
def catalogue(make_product):
    make_product(name="Navy Polo", category="tops", stock=5)
    make_product(name="Grey Hoodie", category="tops", stock=0)
    make_product(name="Barrel Jeans", category="bottoms", stock=3)
    make_product(name="Bucket Hat", category="hats", stock=9)
    make_product(name="Hidden Polo", category="tops", stock=4, isAvailable=False)


def names(response):
    assert response.status_code == 200, response.text
    return {p["name"] for p in response.json()["items"]}


def test_search_by_name_ignores_case(client, catalogue):
    assert names(client.get(URL, params={"q": "POLO"})) == {"Navy Polo"}


def test_search_treats_percent_as_a_character(client, catalogue):
    assert names(client.get(URL, params={"q": "%"})) == set()


def test_filter_by_category_and_stock(client, catalogue):
    assert names(client.get(URL, params={"category": "tops"})) == {"Navy Polo", "Grey Hoodie"}
    assert names(client.get(URL, params={"category": "tops", "inStock": "true"})) == {"Navy Polo"}
    assert names(client.get(URL, params={"inStock": "false"})) == {"Grey Hoodie"}


def test_admin_can_filter_by_availability(client, catalogue):
    assert names(client.get(ADMIN_URL, params={"isAvailable": "false"})) == {"Hidden Polo"}
    assert client.get(ADMIN_URL).json()["total"] == 5


def test_pagination(client, catalogue):
    first = client.get(URL, params={"size": 3}).json()
    second = client.get(URL, params={"size": 3, "page": 2}).json()
    assert (first["total"], first["pages"], len(first["items"]), len(second["items"])) == (4, 2, 3, 1)
    # Newest first, and nothing repeated between pages
    assert first["items"][0]["name"] == "Bucket Hat"
    assert not {p["id"] for p in first["items"]} & {p["id"] for p in second["items"]}


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}, {"category": "shoes"}])
def test_bad_list_parameters_are_rejected(client, params):
    assert client.get(URL, params=params).status_code == 422
