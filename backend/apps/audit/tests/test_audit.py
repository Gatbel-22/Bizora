from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.core.testing import make_member_client, make_owner

AUDIT_URL = "/api/audit-log/"
PRODUCTS_URL = "/api/products/"
CATEGORIES_URL = "/api/categories/"
CUSTOMERS_URL = "/api/customers/"


def product_payload(**overrides):
    payload = {
        "name": "Cola",
        "sku": "COLA",
        "selling_price": "1000.00",
        "purchase_price": "800.00",
        "unit": "BOTTLE",
        "opening_stock": "24",
    }
    payload.update(overrides)
    return payload


class AuditTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")

    def entries(self, client=None, **params):
        response = (client or self.owner_a).get(AUDIT_URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["results"]

    def create_product(self, **overrides):
        response = self.owner_a.post(PRODUCTS_URL, product_payload(**overrides), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def test_creating_a_product_records_who_and_what(self):
        self.create_product()
        entry = self.entries(object_type="product")[0]
        self.assertEqual(entry["action"], "product.created")
        self.assertEqual(entry["object_label"], "Cola")
        self.assertEqual(entry["actor_name"], "Owner of A Mart")
        self.assertEqual(entry["changes"]["name"]["new"], "Cola")

    def test_updating_a_product_records_old_and_new_values(self):
        product = self.create_product()
        self.owner_a.patch(
            f"{PRODUCTS_URL}{product['id']}/",
            {"selling_price": "1200.00"},
            format="json",
        )
        entry = self.entries(action="product.updated")[0]
        self.assertEqual(entry["changes"], {"selling_price": {"old": "1000.00", "new": "1200.00"}})

    def test_saving_without_changes_is_not_logged(self):
        product = self.create_product()
        self.owner_a.patch(
            f"{PRODUCTS_URL}{product['id']}/",
            {"selling_price": "1000.00"},
            format="json",
        )
        self.assertEqual(self.entries(action="product.updated"), [])

    def test_stock_adjustments_are_logged(self):
        product = self.create_product()
        self.owner_a.post(
            f"{PRODUCTS_URL}{product['id']}/stock/",
            {"adjustment_type": "STOCK_OUT", "quantity": "4", "note": "Damaged"},
            format="json",
        )
        entry = self.entries(action="product.stock_adjusted")[0]
        self.assertEqual(entry["object_label"], "Cola")
        self.assertEqual(entry["metadata"]["note"], "Damaged")
        self.assertEqual(float(entry["metadata"]["stock_after"]), 20.0)

    def test_deleting_a_category_is_logged_with_its_name(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Temp"}, format="json").data
        self.owner_a.delete(f"{CATEGORIES_URL}{category['id']}/")
        entry = self.entries(action="category.deleted")[0]
        self.assertEqual(entry["object_label"], "Temp")
        self.assertEqual(entry["object_id"], str(category["id"]))

    def test_a_blocked_delete_leaves_no_deleted_entry(self):
        category = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.create_product(category=category["id"])
        response = self.owner_a.delete(f"{CATEGORIES_URL}{category['id']}/")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.entries(action="category.deleted"), [])

    def test_customer_changes_are_logged(self):
        customer = self.owner_a.post(CUSTOMERS_URL, {"name": "Mama Rose"}, format="json").data
        self.owner_a.patch(f"{CUSTOMERS_URL}{customer['id']}/", {"phone": "0911"}, format="json")
        actions = [e["action"] for e in self.entries(object_type="customer")]
        self.assertEqual(sorted(actions), ["customer.created", "customer.updated"])

    def test_log_can_be_filtered_to_one_record(self):
        product = self.create_product()
        self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json")
        results = self.entries(object_id=product["id"])
        self.assertEqual({e["object_type"] for e in results}, {"product"})

    def test_only_the_owner_can_read_the_log(self):
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        self.assertEqual(manager.get(AUDIT_URL).status_code, 403)
        self.assertEqual(staff.get(AUDIT_URL).status_code, 403)
        self.assertEqual(APIClient().get(AUDIT_URL).status_code, 401)

    def test_other_businesses_cannot_see_the_log(self):
        self.create_product()
        self.assertEqual(self.entries(client=self.owner_b), [])
        entry_id = self.entries()[0]["id"]
        self.assertEqual(self.owner_b.get(f"{AUDIT_URL}{entry_id}/").status_code, 404)

    def test_entries_can_never_be_edited_or_deleted(self):
        self.create_product()
        entry = AuditLog.objects.first()
        entry.action = "tampered"
        with self.assertRaises(ValueError):
            entry.save()
        with self.assertRaises(ValueError):
            entry.delete()
