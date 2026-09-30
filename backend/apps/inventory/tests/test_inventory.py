from decimal import Decimal

from django.core.cache import cache
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient, APITestCase

from apps.businesses.models import Business
from apps.core.testing import make_member_client, make_owner
from apps.inventory import services
from apps.inventory.exceptions import InsufficientStockError
from apps.inventory.models import Category, MovementType, Product, StockMovement

CATEGORIES_URL = "/api/categories/"
SUPPLIERS_URL = "/api/suppliers/"
PRODUCTS_URL = "/api/products/"
MOVEMENTS_URL = "/api/inventory/movements/"


def product_payload(**overrides):
    payload = {
        "name": "Cola 500ml",
        "sku": "COLA-500",
        "selling_price": "1000.00",
        "purchase_price": "800.00",
        "unit": "BOTTLE",
        "min_stock_threshold": "10",
        "opening_stock": "24",
    }
    payload.update(overrides)
    return payload


class InventoryTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")

    def create_product(self, client=None, **overrides):
        response = (client or self.owner_a).post(
            PRODUCTS_URL, product_payload(**overrides), format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def stock_of(self, product):
        return Product.objects.get(pk=product["id"]).current_stock

    def adjust(self, product, client=None, **payload):
        return (client or self.owner_a).post(
            f"{PRODUCTS_URL}{product['id']}/stock/", payload, format="json"
        )


class ProductTests(InventoryTestCase):
    def test_create_product_records_opening_stock(self):
        product = self.create_product()
        self.assertEqual(Decimal(product["current_stock"]), Decimal("24"))
        self.assertEqual(product["stock_status"], "in_stock")
        movement = StockMovement.objects.get()
        self.assertEqual(movement.movement_type, MovementType.OPENING)
        self.assertEqual(movement.stock_after, Decimal("24"))

    def test_create_without_opening_stock_starts_at_zero(self):
        product = self.create_product(opening_stock="0")
        self.assertEqual(Decimal(product["current_stock"]), Decimal("0"))
        self.assertEqual(product["stock_status"], "out")
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_sku_is_stored_uppercase_and_must_be_unique_ignoring_case(self):
        first = self.create_product(sku="cola-1")
        self.assertEqual(first["sku"], "COLA-1")
        response = self.owner_a.post(
            PRODUCTS_URL, product_payload(name="Other", sku="COLA-1"), format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("sku", response.data["error"]["details"])

    def test_same_sku_is_allowed_in_a_different_business(self):
        self.create_product(sku="SHARED")
        self.create_product(client=self.owner_b, sku="SHARED")

    def test_blank_skus_never_conflict(self):
        self.create_product(name="A", sku="")
        self.create_product(name="B", sku="")

    def test_negative_values_are_rejected(self):
        for field in (
            "selling_price",
            "purchase_price",
            "min_stock_threshold",
            "opening_stock",
        ):
            response = self.owner_a.post(
                PRODUCTS_URL, product_payload(sku="X", **{field: "-1"}), format="json"
            )
            self.assertEqual(response.status_code, 400, field)
            self.assertIn(field, response.data["error"]["details"])

    def test_editing_a_product_cannot_change_its_stock(self):
        product = self.create_product()
        response = self.owner_a.patch(
            f"{PRODUCTS_URL}{product['id']}/",
            {"current_stock": "999", "selling_price": "1200.00"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.data["selling_price"]), Decimal("1200"))
        self.assertEqual(self.stock_of(product), Decimal("24"))

    def test_opening_stock_is_rejected_on_update(self):
        product = self.create_product()
        response = self.owner_a.patch(
            f"{PRODUCTS_URL}{product['id']}/", {"opening_stock": "5"}, format="json"
        )
        self.assertEqual(response.status_code, 400)

    def test_products_cannot_be_deleted(self):
        product = self.create_product()
        response = self.owner_a.delete(f"{PRODUCTS_URL}{product['id']}/")
        self.assertEqual(response.status_code, 405)

    def test_search_and_filters(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.create_product(name="Cola", sku="COLA", category=category["id"], opening_stock="24")
        self.create_product(name="Fanta", sku="FANTA", opening_stock="5")  # low: threshold is 10
        water = self.create_product(name="Water", sku="WATER", opening_stock="0")  # out

        def names(**params):
            response = self.owner_a.get(PRODUCTS_URL, params)
            self.assertEqual(response.status_code, 200)
            return sorted(p["name"] for p in response.data["results"])

        self.assertEqual(names(search="col"), ["Cola"])
        self.assertEqual(names(stock_status="low"), ["Fanta"])
        self.assertEqual(names(stock_status="out"), ["Water"])
        self.assertEqual(names(stock_status="in_stock"), ["Cola"])
        self.assertEqual(names(category=category["id"]), ["Cola"])

        self.owner_a.patch(f"{PRODUCTS_URL}{water['id']}/", {"is_active": False}, format="json")
        self.assertEqual(names(is_active="true"), ["Cola", "Fanta"])

    def test_results_are_paginated(self):
        for index in range(3):
            self.create_product(name=f"Item {index}", sku=f"ITEM-{index}")
        response = self.owner_a.get(PRODUCTS_URL, {"page_size": 2})
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])


class CategoryTests(InventoryTestCase):
    def test_duplicate_names_are_rejected_ignoring_case(self):
        self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json")
        response = self.owner_a.post(CATEGORIES_URL, {"name": "beverages"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["error"]["details"])

    def test_list_includes_product_counts(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.create_product(category=category["id"])
        results = self.owner_a.get(CATEGORIES_URL).data["results"]
        self.assertEqual(results[0]["product_count"], 1)

    def test_empty_category_can_be_deleted(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Temp"}, format="json").data
        response = self.owner_a.delete(f"{CATEGORIES_URL}{category['id']}/")
        self.assertEqual(response.status_code, 204)

    def test_category_with_products_cannot_be_deleted(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.create_product(category=category["id"])
        response = self.owner_a.delete(f"{CATEGORIES_URL}{category['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Category.objects.filter(pk=category["id"]).exists())


class StockTests(InventoryTestCase):
    def test_stock_in_adds_stock_and_records_movement(self):
        product = self.create_product()
        response = self.adjust(
            product, adjustment_type="STOCK_IN", quantity="10", unit_cost="800.00"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["movement_type"], "STOCK_IN")
        self.assertEqual(Decimal(response.data["stock_after"]), Decimal("34"))
        self.assertEqual(self.stock_of(product), Decimal("34"))

    def test_fractional_quantities_are_supported(self):
        product = self.create_product()
        self.adjust(product, adjustment_type="STOCK_IN", quantity="2.5")
        self.assertEqual(self.stock_of(product), Decimal("26.5"))

    def test_stock_out_removes_stock_as_a_manual_adjustment(self):
        product = self.create_product()
        response = self.adjust(
            product,
            adjustment_type="STOCK_OUT",
            quantity="4",
            note="Damaged in transit",
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["movement_type"], "ADJUSTMENT")
        self.assertEqual(Decimal(response.data["quantity_change"]), Decimal("-4"))
        self.assertEqual(self.stock_of(product), Decimal("20"))

    def test_removing_stock_requires_a_reason(self):
        product = self.create_product()
        response = self.adjust(product, adjustment_type="STOCK_OUT", quantity="4")
        self.assertEqual(response.status_code, 400)
        self.assertIn("note", response.data["error"]["details"])
        self.assertEqual(self.stock_of(product), Decimal("24"))

    def test_cannot_remove_more_than_is_in_stock(self):
        product = self.create_product()
        response = self.adjust(product, adjustment_type="STOCK_OUT", quantity="100", note="Oops")
        self.assertEqual(response.status_code, 400)
        self.assertIn("quantity", response.data["error"]["details"])
        self.assertEqual(self.stock_of(product), Decimal("24"))
        self.assertEqual(StockMovement.objects.count(), 1)  # only the opening stock line

    def test_stock_count_sets_stock_and_records_the_difference(self):
        product = self.create_product()
        response = self.adjust(product, adjustment_type="COUNT", quantity="20", note="Shelf count")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Decimal(response.data["quantity_change"]), Decimal("-4"))
        self.assertEqual(self.stock_of(product), Decimal("20"))

    def test_count_matching_current_stock_is_rejected(self):
        product = self.create_product()
        response = self.adjust(product, adjustment_type="COUNT", quantity="24", note="Recount")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_zero_and_negative_quantities_are_rejected(self):
        product = self.create_product()
        for quantity in ("0", "-2"):
            response = self.adjust(product, adjustment_type="STOCK_IN", quantity=quantity)
            self.assertEqual(response.status_code, 400, quantity)
        self.assertEqual(self.stock_of(product), Decimal("24"))

    def test_history_lists_newest_first_and_filters_by_product(self):
        first = self.create_product()
        other = self.create_product(name="Water", sku="WATER")
        self.adjust(first, adjustment_type="STOCK_IN", quantity="5")

        response = self.owner_a.get(MOVEMENTS_URL, {"product": first["id"]})
        self.assertEqual(response.status_code, 200)
        types = [m["movement_type"] for m in response.data["results"]]
        self.assertEqual(types, ["STOCK_IN", "OPENING"])
        self.assertEqual(self.owner_a.get(MOVEMENTS_URL).data["count"], 3)
        self.assertIsNotNone(other)

    def test_movements_can_never_be_edited_or_deleted(self):
        self.create_product()
        movement = StockMovement.objects.get()
        movement.note = "changed"
        with self.assertRaises(ValueError):
            movement.save()
        with self.assertRaises(ValueError):
            movement.delete()

    def test_database_refuses_negative_stock(self):
        product = self.create_product()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.filter(pk=product["id"]).update(current_stock=Decimal("-1"))

    def test_service_leaves_no_trace_when_stock_is_insufficient(self):
        product = self.create_product()
        business = Business.objects.get(name="A Mart")
        with self.assertRaises(InsufficientStockError):
            services.record_movement(
                business=business,
                product_id=product["id"],
                movement_type=MovementType.SALE,
                change=Decimal("-100"),
                user=None,
            )
        self.assertEqual(self.stock_of(product), Decimal("24"))
        self.assertEqual(StockMovement.objects.count(), 1)


class PermissionTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        self.staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        self.manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        self.product = self.create_product()

    def test_unauthenticated_requests_are_rejected(self):
        self.assertEqual(APIClient().get(PRODUCTS_URL).status_code, 401)

    def test_staff_can_view_products_but_never_see_cost_prices(self):
        listing = self.staff.get(PRODUCTS_URL)
        self.assertEqual(listing.status_code, 200)
        self.assertNotIn("purchase_price", listing.data["results"][0])
        detail = self.staff.get(f"{PRODUCTS_URL}{self.product['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("purchase_price", detail.data)

    def test_owner_and_manager_do_see_cost_prices(self):
        self.assertIn("purchase_price", self.owner_a.get(PRODUCTS_URL).data["results"][0])
        self.assertIn("purchase_price", self.manager.get(PRODUCTS_URL).data["results"][0])

    def test_staff_cannot_change_anything(self):
        url = f"{PRODUCTS_URL}{self.product['id']}/"
        self.assertEqual(
            self.staff.post(PRODUCTS_URL, product_payload(sku="NEW"), format="json").status_code,
            403,
        )
        self.assertEqual(
            self.staff.patch(url, {"selling_price": "1"}, format="json").status_code,
            403,
        )
        self.assertEqual(
            self.adjust(
                self.product,
                client=self.staff,
                adjustment_type="STOCK_IN",
                quantity="1",
            ).status_code,
            403,
        )
        self.assertEqual(self.staff.get(MOVEMENTS_URL).status_code, 403)
        self.assertEqual(
            self.staff.post(CATEGORIES_URL, {"name": "X"}, format="json").status_code,
            403,
        )
        self.assertEqual(self.staff.get(CATEGORIES_URL).status_code, 200)

    def test_manager_can_manage_the_catalog_and_stock(self):
        created = self.manager.post(PRODUCTS_URL, product_payload(sku="MGR"), format="json")
        self.assertEqual(created.status_code, 201)
        response = self.adjust(
            self.product, client=self.manager, adjustment_type="STOCK_IN", quantity="1"
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.manager.get(MOVEMENTS_URL).status_code, 200)


class TenantIsolationTests(InventoryTestCase):
    def setUp(self):
        super().setUp()
        self.product = self.create_product()
        self.category = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.owner_a.post(SUPPLIERS_URL, {"name": "Juba Wholesale"}, format="json")

    def test_other_business_sees_nothing(self):
        for url in (PRODUCTS_URL, CATEGORIES_URL, SUPPLIERS_URL, MOVEMENTS_URL):
            response = self.owner_b.get(url)
            self.assertEqual(response.status_code, 200, url)
            self.assertEqual(response.data["count"], 0, url)

    def test_other_business_cannot_read_edit_or_adjust_a_product(self):
        url = f"{PRODUCTS_URL}{self.product['id']}/"
        self.assertEqual(self.owner_b.get(url).status_code, 404)
        self.assertEqual(
            self.owner_b.patch(url, {"selling_price": "1"}, format="json").status_code,
            404,
        )
        response = self.adjust(
            self.product, client=self.owner_b, adjustment_type="STOCK_IN", quantity="50"
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.stock_of(self.product), Decimal("24"))

    def test_other_business_cannot_delete_a_category(self):
        response = self.owner_b.delete(f"{CATEGORIES_URL}{self.category['id']}/")
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Category.objects.filter(pk=self.category["id"]).exists())

    def test_cannot_attach_another_businesses_category_or_supplier(self):
        foreign_category = self.owner_b.post(CATEGORIES_URL, {"name": "Secret"}, format="json").data
        foreign_supplier = self.owner_b.post(
            SUPPLIERS_URL, {"name": "Secret Supplier"}, format="json"
        ).data

        response = self.owner_a.post(
            PRODUCTS_URL,
            product_payload(sku="NEW-1", category=foreign_category["id"]),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data["error"]["details"])

        response = self.owner_a.post(
            PRODUCTS_URL,
            product_payload(sku="NEW-2", supplier=foreign_supplier["id"]),
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("supplier", response.data["error"]["details"])
