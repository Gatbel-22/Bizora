from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.core.testing import make_member_client, make_owner
from apps.expenses.models import Expense, ExpenseCategory
from apps.inventory.models import Product

CATEGORIES_URL = "/api/expense-categories/"
EXPENSES_URL = "/api/expenses/"
SUMMARY_URL = "/api/expenses/summary/"
SUPPLIERS_URL = "/api/suppliers/"
PRODUCTS_URL = "/api/products/"

DEFAULT_NAMES = {
    "Rent",
    "Salaries",
    "Utilities",
    "Transport",
    "Inventory",
    "Marketing",
    "Maintenance",
    "Communication",
    "Taxes & fees",
    "Other",
}


def days_from_today(days):
    return (timezone.localdate() + timedelta(days=days)).isoformat()


class ExpenseTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")

    def category_id(self, name, client=None):
        response = (client or self.owner_a).get(CATEGORIES_URL, {"page_size": 100})
        return next(c["id"] for c in response.data["results"] if c["name"] == name)

    def create_expense(self, client=None, **overrides):
        category = overrides.pop("category", None) or self.category_id("Rent", client)
        payload = {
            "description": "Shop rent for October",
            "category": category,
            "amount": "150000.00",
            "payment_method": "CASH",
        }
        payload.update(overrides)
        response = (client or self.owner_a).post(EXPENSES_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def descriptions(self, **params):
        response = self.owner_a.get(EXPENSES_URL, params)
        self.assertEqual(response.status_code, 200, response.data)
        return sorted(e["description"] for e in response.data["results"])


class CategoryTests(ExpenseTestCase):
    def test_new_businesses_get_the_default_categories(self):
        results = self.owner_a.get(CATEGORIES_URL, {"page_size": 100}).data["results"]
        self.assertEqual({c["name"] for c in results}, DEFAULT_NAMES)
        flags = {c["name"]: c["affects_profit"] for c in results}
        self.assertFalse(flags["Inventory"])
        self.assertTrue(flags["Rent"])

    def test_each_business_has_its_own_categories(self):
        ids_a = {c["id"] for c in self.owner_a.get(CATEGORIES_URL).data["results"]}
        ids_b = {c["id"] for c in self.owner_b.get(CATEGORIES_URL).data["results"]}
        self.assertEqual(len(ids_b), 10)
        self.assertEqual(ids_a & ids_b, set())

    def test_categories_can_be_added_and_changed(self):
        created = self.owner_a.post(CATEGORIES_URL, {"name": "Security"}, format="json")
        self.assertEqual(created.status_code, 201, created.data)
        self.assertTrue(created.data["affects_profit"])
        changed = self.owner_a.patch(
            f"{CATEGORIES_URL}{created.data['id']}/", {"affects_profit": False}, format="json"
        )
        self.assertEqual(changed.status_code, 200)
        self.assertFalse(ExpenseCategory.objects.get(pk=created.data["id"]).affects_profit)

    def test_duplicate_names_are_rejected_ignoring_case(self):
        response = self.owner_a.post(CATEGORIES_URL, {"name": "rent"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("name", response.data["error"]["details"])

    def test_a_category_with_expenses_cannot_be_deleted(self):
        self.create_expense()
        response = self.owner_a.delete(f"{CATEGORIES_URL}{self.category_id('Rent')}/")
        self.assertEqual(response.status_code, 400)
        self.assertTrue(
            ExpenseCategory.objects.filter(name="Rent", business__name="A Mart").exists()
        )

    def test_an_unused_category_can_be_deleted(self):
        response = self.owner_a.delete(f"{CATEGORIES_URL}{self.category_id('Other')}/")
        self.assertEqual(response.status_code, 204)

    def test_staff_have_no_access_but_managers_do(self):
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        self.assertEqual(staff.get(CATEGORIES_URL).status_code, 403)
        self.assertEqual(manager.get(CATEGORIES_URL).status_code, 200)
        response = manager.post(CATEGORIES_URL, {"name": "Security"}, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(APIClient().get(CATEGORIES_URL).status_code, 401)

    def test_category_changes_are_audited(self):
        self.owner_a.post(CATEGORIES_URL, {"name": "Security"}, format="json")
        self.assertTrue(AuditLog.objects.filter(action="expensecategory.created").exists())


class ExpenseTests(ExpenseTestCase):
    def test_create_an_expense(self):
        data = self.create_expense()
        self.assertEqual(Decimal(data["amount"]), Decimal("150000"))
        self.assertEqual(data["category_name"], "Rent")
        self.assertTrue(data["category_affects_profit"])
        self.assertEqual(data["expense_date"], timezone.localdate().isoformat())
        self.assertEqual(data["created_by_name"], "Owner of A Mart")
        self.assertEqual(data["payment_method"], "CASH")

    def test_amount_must_be_positive(self):
        for amount in ("0", "-5"):
            response = self.owner_a.post(
                EXPENSES_URL,
                {
                    "description": "Bad",
                    "category": self.category_id("Rent"),
                    "amount": amount,
                    "payment_method": "CASH",
                },
                format="json",
            )
            self.assertEqual(response.status_code, 400, amount)
            self.assertIn("amount", response.data["error"]["details"])

    def test_dates_must_be_real_and_not_in_the_future(self):
        category = self.category_id("Rent")
        for value in (days_from_today(1), "31-31-2026"):
            response = self.owner_a.post(
                EXPENSES_URL,
                {
                    "description": "Bad date",
                    "category": category,
                    "amount": "10.00",
                    "payment_method": "CASH",
                    "expense_date": value,
                },
                format="json",
            )
            self.assertEqual(response.status_code, 400, value)
            self.assertIn("expense_date", response.data["error"]["details"])

    def test_credit_is_not_a_payment_method_for_expenses(self):
        response = self.owner_a.post(
            EXPENSES_URL,
            {
                "description": "On tab",
                "category": self.category_id("Rent"),
                "amount": "10.00",
                "payment_method": "CREDIT",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("payment_method", response.data["error"]["details"])

    def test_description_and_category_are_required(self):
        response = self.owner_a.post(
            EXPENSES_URL, {"amount": "10.00", "payment_method": "CASH"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        details = response.data["error"]["details"]
        self.assertIn("description", details)
        self.assertIn("category", details)

    def test_another_businesses_category_or_supplier_is_rejected(self):
        foreign_category = self.category_id("Rent", client=self.owner_b)
        foreign_supplier = self.owner_b.post(
            SUPPLIERS_URL, {"name": "Their supplier"}, format="json"
        ).data
        payload = {
            "description": "Sneaky",
            "category": foreign_category,
            "amount": "10.00",
            "payment_method": "CASH",
        }
        response = self.owner_a.post(EXPENSES_URL, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("category", response.data["error"]["details"])

        payload["category"] = self.category_id("Rent")
        payload["supplier"] = foreign_supplier["id"]
        response = self.owner_a.post(EXPENSES_URL, payload, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertIn("supplier", response.data["error"]["details"])
        self.assertEqual(Expense.objects.count(), 0)

    def test_editing_is_audited_with_old_and_new_values(self):
        expense = self.create_expense()
        response = self.owner_a.patch(
            f"{EXPENSES_URL}{expense['id']}/", {"amount": "160000.00"}, format="json"
        )
        self.assertEqual(response.status_code, 200)
        entry = AuditLog.objects.get(action="expense.updated")
        self.assertEqual(entry.changes["amount"], {"old": "150000.00", "new": "160000.00"})

    def test_audit_log_shows_names_instead_of_ids(self):
        expense = self.create_expense()
        created = AuditLog.objects.get(action="expense.created")
        self.assertEqual(created.changes["category"]["new"], "Rent")
        self.owner_a.patch(
            f"{EXPENSES_URL}{expense['id']}/",
            {"category": self.category_id("Utilities")},
            format="json",
        )
        updated = AuditLog.objects.get(action="expense.updated")
        self.assertEqual(updated.changes["category"], {"old": "Rent", "new": "Utilities"})

    def test_only_the_owner_can_delete_and_it_is_audited(self):
        expense = self.create_expense()
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        url = f"{EXPENSES_URL}{expense['id']}/"
        self.assertEqual(manager.delete(url).status_code, 403)
        self.assertTrue(Expense.objects.filter(pk=expense["id"]).exists())
        self.assertEqual(self.owner_a.delete(url).status_code, 204)
        self.assertFalse(Expense.objects.filter(pk=expense["id"]).exists())
        entry = AuditLog.objects.get(action="expense.deleted")
        self.assertEqual(entry.object_label, "Shop rent for October")

    def test_managers_can_record_and_edit(self):
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        expense = self.create_expense(client=manager)
        response = manager.patch(
            f"{EXPENSES_URL}{expense['id']}/", {"notes": "Paid in full"}, format="json"
        )
        self.assertEqual(response.status_code, 200)

    def test_staff_cannot_see_or_record_expenses(self):
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        self.assertEqual(staff.get(EXPENSES_URL).status_code, 403)
        self.assertEqual(staff.get(SUMMARY_URL).status_code, 403)
        response = staff.post(
            EXPENSES_URL,
            {
                "description": "X",
                "category": self.category_id("Rent"),
                "amount": "10.00",
                "payment_method": "CASH",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 403)

    def test_unauthenticated_requests_are_refused(self):
        self.assertEqual(APIClient().get(EXPENSES_URL).status_code, 401)

    def test_a_supplier_can_be_linked_and_deleting_it_keeps_the_expense(self):
        supplier = self.owner_a.post(SUPPLIERS_URL, {"name": "Landlord Ltd"}, format="json").data
        expense = self.create_expense(supplier=supplier["id"])
        self.assertEqual(expense["supplier_name"], "Landlord Ltd")
        self.assertEqual(self.owner_a.delete(f"{SUPPLIERS_URL}{supplier['id']}/").status_code, 204)
        self.assertIsNone(Expense.objects.get(pk=expense["id"]).supplier)


class ExpenseListTests(ExpenseTestCase):
    def setUp(self):
        super().setUp()
        self.transport = self.category_id("Transport")
        self.create_expense(
            description="Rent", amount="100000.00", expense_date=days_from_today(-40)
        )
        self.create_expense(
            description="Taxi",
            category=self.transport,
            amount="2000.00",
            payment_method="MOBILE_MONEY",
            expense_date=days_from_today(-2),
        )
        self.create_expense(
            description="Fuel",
            category=self.transport,
            amount="5000.00",
            expense_date=days_from_today(-1),
        )

    def test_newest_expenses_come_first(self):
        response = self.owner_a.get(EXPENSES_URL)
        self.assertEqual(
            [e["description"] for e in response.data["results"]], ["Fuel", "Taxi", "Rent"]
        )

    def test_filters(self):
        self.assertEqual(self.descriptions(category=self.transport), ["Fuel", "Taxi"])
        self.assertEqual(self.descriptions(payment_method="MOBILE_MONEY"), ["Taxi"])
        self.assertEqual(self.descriptions(date_from=days_from_today(-5)), ["Fuel", "Taxi"])
        self.assertEqual(self.descriptions(date_to=days_from_today(-10)), ["Rent"])
        self.assertEqual(self.descriptions(min_amount="3000"), ["Fuel", "Rent"])
        self.assertEqual(self.descriptions(max_amount="3000"), ["Taxi"])

    def test_search_covers_description_and_category(self):
        self.assertEqual(self.descriptions(search="taxi"), ["Taxi"])
        self.assertEqual(self.descriptions(search="transport"), ["Fuel", "Taxi"])

    def test_an_invalid_date_filter_is_refused(self):
        response = self.owner_a.get(EXPENSES_URL, {"date_from": "not-a-date"})
        self.assertEqual(response.status_code, 400)

    def test_results_are_paginated(self):
        response = self.owner_a.get(EXPENSES_URL, {"page_size": 2})
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 2)
        self.assertIsNotNone(response.data["next"])

    def test_summary_totals_and_breakdown(self):
        data = self.owner_a.get(SUMMARY_URL).data
        self.assertEqual(Decimal(data["total"]), Decimal("107000"))
        self.assertEqual(data["count"], 3)
        self.assertEqual(
            [(row["name"], Decimal(row["total"])) for row in data["by_category"]],
            [("Rent", Decimal("100000")), ("Transport", Decimal("7000"))],
        )
        self.assertTrue(data["by_category"][0]["affects_profit"])

    def test_summary_respects_filters(self):
        data = self.owner_a.get(SUMMARY_URL, {"date_from": days_from_today(-5)}).data
        self.assertEqual(Decimal(data["total"]), Decimal("7000"))
        self.assertEqual(data["count"], 2)

    def test_summary_with_no_expenses_is_zero(self):
        data = self.owner_b.get(SUMMARY_URL).data
        self.assertEqual(Decimal(data["total"]), Decimal("0"))
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["by_category"], [])


class ExpenseTenantIsolationTests(ExpenseTestCase):
    def test_other_businesses_cannot_see_or_touch_expenses(self):
        expense = self.create_expense()
        url = f"{EXPENSES_URL}{expense['id']}/"
        self.assertEqual(self.owner_b.get(EXPENSES_URL).data["count"], 0)
        self.assertEqual(self.owner_b.get(url).status_code, 404)
        self.assertEqual(
            self.owner_b.patch(url, {"amount": "1.00"}, format="json").status_code, 404
        )
        self.assertEqual(self.owner_b.delete(url).status_code, 404)
        self.assertEqual(Decimal(self.owner_b.get(SUMMARY_URL).data["total"]), Decimal("0"))
        self.assertTrue(Expense.objects.filter(pk=expense["id"]).exists())

    def test_other_businesses_cannot_change_our_categories(self):
        rent = self.category_id("Rent")
        url = f"{CATEGORIES_URL}{rent}/"
        self.assertEqual(self.owner_b.patch(url, {"name": "X"}, format="json").status_code, 404)
        self.assertEqual(self.owner_b.delete(url).status_code, 404)


class SupplierTests(ExpenseTestCase):
    def test_suppliers_show_how_many_products_use_them(self):
        supplier = self.owner_a.post(SUPPLIERS_URL, {"name": "Juba Wholesale"}, format="json").data
        self.owner_a.post(
            PRODUCTS_URL,
            {"name": "Cola", "sku": "COLA", "selling_price": "1000.00", "supplier": supplier["id"]},
            format="json",
        )
        results = self.owner_a.get(SUPPLIERS_URL).data["results"]
        self.assertEqual(results[0]["product_count"], 1)

    def test_deleting_a_supplier_keeps_its_products(self):
        supplier = self.owner_a.post(SUPPLIERS_URL, {"name": "Juba Wholesale"}, format="json").data
        product = self.owner_a.post(
            PRODUCTS_URL,
            {"name": "Cola", "sku": "COLA", "selling_price": "1000.00", "supplier": supplier["id"]},
            format="json",
        ).data
        self.assertEqual(self.owner_a.delete(f"{SUPPLIERS_URL}{supplier['id']}/").status_code, 204)
        self.assertIsNone(Product.objects.get(pk=product["id"]).supplier)
        self.assertTrue(AuditLog.objects.filter(action="supplier.deleted").exists())
