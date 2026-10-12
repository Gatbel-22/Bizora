from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.audit.models import AuditLog
from apps.core.testing import make_member_client, make_owner
from apps.customers.models import Receivable
from apps.inventory.models import MovementType, Product, StockMovement
from apps.sales.models import Sale, SaleStatus

SALES_URL = "/api/sales/"
PRODUCTS_URL = "/api/products/"
CUSTOMERS_URL = "/api/customers/"
RECEIVABLES_URL = "/api/receivables/"
PAYMENTS_URL = "/api/customer-payments/"


class SalesTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")
        self.cola = self.create_product(self.owner_a, "Cola", "COLA", "1000.00", "800.00", "24")
        self.water = self.create_product(self.owner_a, "Water", "WATER", "500.00", "300.00", "10")

    def create_product(self, client, name, sku, selling, cost, stock):
        response = client.post(
            PRODUCTS_URL,
            {
                "name": name,
                "sku": sku,
                "selling_price": selling,
                "purchase_price": cost,
                "unit": "PIECE",
                "opening_stock": stock,
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def create_customer(self, client=None, name="Mama Rose"):
        response = (client or self.owner_a).post(CUSTOMERS_URL, {"name": name}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def sell(self, lines, client=None, **extra):
        """lines: (product, quantity) or (product, quantity, line_discount) tuples."""
        items = []
        for line in lines:
            item = {"product": line[0]["id"], "quantity": line[1]}
            if len(line) > 2:
                item["discount"] = line[2]
            items.append(item)
        payload = {"items": items, "payment_method": "CASH"}
        payload.update(extra)
        return (client or self.owner_a).post(SALES_URL, payload, format="json")

    def stock_of(self, product):
        return Product.objects.get(pk=product["id"]).current_stock

    def cancel(self, sale, client=None, reason="Customer changed their mind"):
        return (client or self.owner_a).post(
            f"{SALES_URL}{sale['id']}/cancel/", {"reason": reason}, format="json"
        )

    def customer_detail(self, customer):
        return self.owner_a.get(f"{CUSTOMERS_URL}{customer['id']}/").data


class CashSaleTests(SalesTestCase):
    def test_cash_sale_records_everything(self):
        response = self.sell([(self.cola, "3"), (self.water, "2")])
        self.assertEqual(response.status_code, 201, response.data)
        data = response.data
        self.assertEqual(data["number"], "S-000001")
        self.assertEqual(data["status"], "COMPLETED")
        self.assertEqual(Decimal(data["subtotal"]), Decimal("4000"))
        self.assertEqual(Decimal(data["total"]), Decimal("4000"))
        self.assertEqual(Decimal(data["amount_paid"]), Decimal("4000"))
        self.assertEqual(Decimal(data["outstanding_amount"]), Decimal("0"))
        self.assertEqual({item["product_name"] for item in data["items"]}, {"Cola", "Water"})
        self.assertEqual(len(data["payments"]), 1)
        self.assertEqual(self.stock_of(self.cola), Decimal("21"))
        self.assertEqual(self.stock_of(self.water), Decimal("8"))
        sale_movements = StockMovement.objects.filter(movement_type=MovementType.SALE)
        self.assertEqual(sale_movements.count(), 2)
        self.assertEqual(Receivable.objects.count(), 0)

    def test_owner_sees_cost_and_profit(self):
        data = self.sell([(self.cola, "3"), (self.water, "2")]).data
        self.assertEqual(Decimal(data["cost_of_goods_sold"]), Decimal("3000"))
        self.assertEqual(Decimal(data["gross_profit"]), Decimal("1000"))
        self.assertIn("unit_cost", data["items"][0])

    def test_sale_numbers_count_up_separately_for_each_business(self):
        self.assertEqual(self.sell([(self.cola, "1")]).data["number"], "S-000001")
        self.assertEqual(self.sell([(self.cola, "1")]).data["number"], "S-000002")
        theirs = self.create_product(self.owner_b, "Tea", "TEA", "200.00", "100.00", "5")
        response = self.sell([(theirs, "1")], client=self.owner_b)
        self.assertEqual(response.data["number"], "S-000001")

    def test_past_sales_keep_the_price_they_were_sold_at(self):
        sale = self.sell([(self.cola, "1")]).data
        self.owner_a.patch(
            f"{PRODUCTS_URL}{self.cola['id']}/",
            {"selling_price": "2000.00"},
            format="json",
        )
        detail = self.owner_a.get(f"{SALES_URL}{sale['id']}/").data
        self.assertEqual(Decimal(detail["items"][0]["unit_price"]), Decimal("1000"))

    def test_sale_discount_reduces_the_total(self):
        data = self.sell([(self.cola, "3"), (self.water, "2")], discount="500.00").data
        self.assertEqual(Decimal(data["subtotal"]), Decimal("4000"))
        self.assertEqual(Decimal(data["total"]), Decimal("3500"))
        self.assertEqual(Decimal(data["amount_paid"]), Decimal("3500"))

    def test_line_discount_reduces_the_line(self):
        data = self.sell([(self.cola, "2", "100.00")]).data
        self.assertEqual(Decimal(data["total"]), Decimal("1900"))
        self.assertEqual(Decimal(data["items"][0]["line_total"]), Decimal("1900"))

    def test_discount_larger_than_the_sale_is_refused(self):
        response = self.sell([(self.cola, "1")], discount="5000.00")
        self.assertEqual(response.status_code, 400)
        self.assertIn("discount", response.data["error"]["details"])

    def test_line_discount_larger_than_the_line_is_refused(self):
        response = self.sell([(self.cola, "1", "5000.00")])
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", response.data["error"]["details"])

    def test_not_enough_stock_is_refused_and_changes_nothing(self):
        response = self.sell([(self.cola, "100")])
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", response.data["error"]["details"])
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(self.stock_of(self.cola), Decimal("24"))
        # The failed attempt didn't use up a sale number.
        self.assertEqual(self.sell([(self.cola, "1")]).data["number"], "S-000001")

    def test_one_failing_line_undoes_the_whole_sale(self):
        response = self.sell([(self.water, "2"), (self.cola, "100")])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stock_of(self.water), Decimal("10"))
        self.assertEqual(Sale.objects.count(), 0)

    def test_inactive_products_cannot_be_sold(self):
        self.owner_a.patch(f"{PRODUCTS_URL}{self.cola['id']}/", {"is_active": False}, format="json")
        response = self.sell([(self.cola, "1")])
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stock_of(self.cola), Decimal("24"))

    def test_another_businesses_product_cannot_be_sold(self):
        theirs = self.create_product(self.owner_b, "Tea", "TEA", "200.00", "100.00", "5")
        response = self.sell([(theirs, "1")])
        self.assertEqual(response.status_code, 400)
        self.assertIn("items", response.data["error"]["details"])
        self.assertEqual(self.stock_of(theirs), Decimal("5"))

    def test_zero_negative_and_missing_items_are_refused(self):
        for quantity in ("0", "-1"):
            self.assertEqual(self.sell([(self.cola, quantity)]).status_code, 400, quantity)
        self.assertEqual(self.sell([]).status_code, 400)
        self.assertEqual(Sale.objects.count(), 0)

    def test_a_sale_worth_nothing_is_refused(self):
        free = self.create_product(self.owner_a, "Freebie", "FREE", "0.00", "0.00", "5")
        self.assertEqual(self.sell([(free, "1")]).status_code, 400)

    def test_unauthenticated_requests_are_refused(self):
        self.assertEqual(APIClient().get(SALES_URL).status_code, 401)
        self.assertEqual(APIClient().post(SALES_URL, {}, format="json").status_code, 401)

    def test_retrying_the_same_request_does_not_create_a_second_sale(self):
        reference = str(uuid4())
        first = self.sell([(self.cola, "2")], client_reference=reference)
        second = self.sell([(self.cola, "2")], client_reference=reference)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(Sale.objects.count(), 1)
        self.assertEqual(self.stock_of(self.cola), Decimal("22"))

    def test_list_filters_and_search(self):
        customer = self.create_customer()
        self.sell([(self.cola, "1")])
        self.sell([(self.cola, "1")], payment_method="CREDIT", customer=customer["id"])
        today = timezone.localdate().isoformat()
        tomorrow = (timezone.localdate() + timedelta(days=1)).isoformat()

        def numbers(**params):
            response = self.owner_a.get(SALES_URL, params)
            self.assertEqual(response.status_code, 200)
            return sorted(s["number"] for s in response.data["results"])

        self.assertEqual(numbers(has_balance="true"), ["S-000002"])
        self.assertEqual(numbers(customer=customer["id"]), ["S-000002"])
        self.assertEqual(numbers(search="S-000001"), ["S-000001"])
        self.assertEqual(numbers(date_from=today), ["S-000001", "S-000002"])
        self.assertEqual(numbers(date_from=tomorrow), [])
        self.assertEqual(numbers(status="CANCELLED"), [])

    def test_database_refuses_inconsistent_balances(self):
        sale = self.sell([(self.cola, "1")]).data
        with self.assertRaises(IntegrityError), transaction.atomic():
            Sale.objects.filter(pk=sale["id"]).update(outstanding_amount=Decimal("1.00"))


class CreditSaleTests(SalesTestCase):
    def test_credit_sale_creates_a_debt(self):
        customer = self.create_customer()
        due = (timezone.localdate() + timedelta(days=14)).isoformat()
        response = self.sell(
            [(self.cola, "4")],
            payment_method="CREDIT",
            customer=customer["id"],
            due_date=due,
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Decimal(response.data["amount_paid"]), Decimal("0"))
        self.assertEqual(Decimal(response.data["outstanding_amount"]), Decimal("4000"))
        self.assertEqual(response.data["payments"], [])

        debts = self.owner_a.get(RECEIVABLES_URL, {"customer": customer["id"]}).data["results"]
        self.assertEqual(len(debts), 1)
        self.assertEqual(Decimal(debts[0]["original_amount"]), Decimal("4000"))
        self.assertEqual(debts[0]["note"], "Credit sale S-000001")
        self.assertEqual(debts[0]["reference_type"], "sale")
        self.assertEqual(debts[0]["due_date"], due)

        detail = self.customer_detail(customer)
        self.assertEqual(Decimal(detail["outstanding_balance"]), Decimal("4000"))
        self.assertEqual(Decimal(detail["total_purchases"]), Decimal("4000"))
        self.assertIsNotNone(detail["last_purchase_at"])

    def test_part_payment_splits_between_cash_and_debt(self):
        customer = self.create_customer()
        response = self.sell([(self.cola, "4")], customer=customer["id"], amount_paid="1500.00")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Decimal(response.data["amount_paid"]), Decimal("1500"))
        self.assertEqual(Decimal(response.data["outstanding_amount"]), Decimal("2500"))
        self.assertEqual(len(response.data["payments"]), 1)
        self.assertEqual(
            Decimal(self.customer_detail(customer)["outstanding_balance"]),
            Decimal("2500"),
        )

    def test_credit_needs_a_customer(self):
        response = self.sell([(self.cola, "1")], payment_method="CREDIT")
        self.assertEqual(response.status_code, 400)
        self.assertIn("customer", response.data["error"]["details"])
        response = self.sell([(self.cola, "4")], amount_paid="1500.00")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(self.stock_of(self.cola), Decimal("24"))

    def test_credit_sale_cannot_also_have_a_payment(self):
        customer = self.create_customer()
        response = self.sell(
            [(self.cola, "1")],
            payment_method="CREDIT",
            customer=customer["id"],
            amount_paid="100.00",
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("amount_paid", response.data["error"]["details"])

    def test_amount_paid_must_be_between_zero_and_the_total(self):
        for amount in ("0", "5000.00"):
            response = self.sell([(self.cola, "1")], amount_paid=amount)
            self.assertEqual(response.status_code, 400, amount)
            self.assertIn("amount_paid", response.data["error"]["details"])

    def test_due_date_cannot_be_in_the_past(self):
        customer = self.create_customer()
        yesterday = (timezone.localdate() - timedelta(days=1)).isoformat()
        response = self.sell(
            [(self.cola, "1")],
            payment_method="CREDIT",
            customer=customer["id"],
            due_date=yesterday,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("due_date", response.data["error"]["details"])

    def test_another_businesses_customer_is_refused(self):
        theirs = self.create_customer(client=self.owner_b, name="Their customer")
        response = self.sell([(self.cola, "1")], payment_method="CREDIT", customer=theirs["id"])
        self.assertEqual(response.status_code, 400)
        self.assertIn("customer", response.data["error"]["details"])

    def test_the_debt_from_a_credit_sale_can_be_paid_off(self):
        customer = self.create_customer()
        self.sell([(self.cola, "4")], payment_method="CREDIT", customer=customer["id"])
        payment = self.owner_a.post(
            PAYMENTS_URL,
            {"customer": customer["id"], "amount": "4000.00", "method": "CASH"},
            format="json",
        )
        self.assertEqual(payment.status_code, 201, payment.data)
        self.assertEqual(
            Decimal(self.customer_detail(customer)["outstanding_balance"]), Decimal("0")
        )


class CancellationTests(SalesTestCase):
    def test_cancelling_returns_stock_and_keeps_the_record(self):
        sale = self.sell([(self.cola, "3")]).data
        response = self.cancel(sale, reason="Wrong item")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "CANCELLED")
        self.assertEqual(response.data["cancel_reason"], "Wrong item")
        self.assertEqual(self.stock_of(self.cola), Decimal("24"))
        returns = StockMovement.objects.filter(movement_type=MovementType.SALE_CANCELLED)
        self.assertEqual(returns.count(), 1)
        self.assertEqual(Sale.objects.get(pk=sale["id"]).status, SaleStatus.CANCELLED)

    def test_cancelling_a_credit_sale_voids_its_debt(self):
        customer = self.create_customer()
        sale = self.sell([(self.cola, "4")], payment_method="CREDIT", customer=customer["id"]).data
        self.assertEqual(self.cancel(sale).status_code, 200)
        detail = self.customer_detail(customer)
        self.assertEqual(Decimal(detail["outstanding_balance"]), Decimal("0"))
        self.assertEqual(Decimal(detail["total_purchases"]), Decimal("0"))
        self.assertEqual(self.owner_a.get(RECEIVABLES_URL).data["count"], 0)
        self.assertIsNotNone(Receivable.objects.get().voided_at)

    def test_a_sale_with_payments_on_its_debt_cannot_be_cancelled(self):
        customer = self.create_customer()
        sale = self.sell([(self.cola, "4")], payment_method="CREDIT", customer=customer["id"]).data
        self.owner_a.post(
            PAYMENTS_URL,
            {"customer": customer["id"], "amount": "100.00", "method": "CASH"},
            format="json",
        )
        response = self.cancel(sale)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(Sale.objects.get(pk=sale["id"]).status, SaleStatus.COMPLETED)
        self.assertEqual(self.stock_of(self.cola), Decimal("20"))

    def test_a_sale_cannot_be_cancelled_twice(self):
        sale = self.sell([(self.cola, "1")]).data
        self.assertEqual(self.cancel(sale).status_code, 200)
        self.assertEqual(self.cancel(sale).status_code, 400)
        self.assertEqual(self.stock_of(self.cola), Decimal("24"))

    def test_a_reason_is_required(self):
        sale = self.sell([(self.cola, "1")]).data
        response = self.owner_a.post(f"{SALES_URL}{sale['id']}/cancel/", {}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.stock_of(self.cola), Decimal("23"))

    def test_staff_cannot_cancel_but_managers_can(self):
        sale = self.sell([(self.cola, "1")]).data
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        self.assertEqual(self.cancel(sale, client=staff).status_code, 403)
        self.assertEqual(self.cancel(sale, client=manager).status_code, 200)

    def test_sales_and_cancellations_are_audited(self):
        sale = self.sell([(self.cola, "1")]).data
        self.cancel(sale)
        actions = set(AuditLog.objects.values_list("action", flat=True))
        self.assertTrue({"sale.created", "sale.cancelled"} <= actions)


class ReceiptAndAccessTests(SalesTestCase):
    def test_receipt_has_everything_needed_to_print(self):
        customer = self.create_customer()
        sale = self.sell([(self.cola, "4")], customer=customer["id"], amount_paid="1500.00").data
        response = self.owner_a.get(f"{SALES_URL}{sale['id']}/receipt/")
        self.assertEqual(response.status_code, 200)
        receipt = response.data
        self.assertEqual(receipt["business"]["name"], "A Mart")
        self.assertEqual(receipt["business"]["currency"], "SSP")
        self.assertEqual(receipt["number"], "S-000001")
        self.assertEqual(receipt["customer"], "Mama Rose")
        self.assertEqual(receipt["served_by"], "Owner of A Mart")
        self.assertEqual(len(receipt["items"]), 1)
        self.assertEqual(Decimal(receipt["outstanding_amount"]), Decimal("2500"))

    def test_staff_can_sell_and_view_but_never_see_costs(self):
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        response = self.sell([(self.cola, "1")], client=staff)
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("gross_profit", response.data)
        self.assertNotIn("cost_of_goods_sold", response.data)
        self.assertNotIn("unit_cost", response.data["items"][0])
        detail = staff.get(f"{SALES_URL}{response.data['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("gross_profit", detail.data)
        self.assertEqual(staff.get(f"{SALES_URL}{response.data['id']}/receipt/").status_code, 200)

    def test_other_businesses_see_nothing(self):
        sale = self.sell([(self.cola, "1")]).data
        self.assertEqual(self.owner_b.get(SALES_URL).data["count"], 0)
        self.assertEqual(self.owner_b.get(f"{SALES_URL}{sale['id']}/").status_code, 404)
        self.assertEqual(self.owner_b.get(f"{SALES_URL}{sale['id']}/receipt/").status_code, 404)
        self.assertEqual(self.cancel(sale, client=self.owner_b).status_code, 404)
        self.assertEqual(Sale.objects.get(pk=sale["id"]).status, SaleStatus.COMPLETED)
