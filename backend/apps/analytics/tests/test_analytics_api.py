from datetime import datetime, time, timedelta
from decimal import Decimal as D

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.businesses.models import Business
from apps.core.testing import make_member_client, make_owner
from apps.customers.models import Receivable
from apps.sales.models import Sale, SaleItem, SaleStatus

PROFIT_URL = "/api/profit/"
DASHBOARD_URL = "/api/dashboard/"
PRODUCTS_URL = "/api/products/"
CATEGORIES_URL = "/api/categories/"
EXPENSE_CATEGORIES_URL = "/api/expense-categories/"
EXPENSES_URL = "/api/expenses/"
SALES_URL = "/api/sales/"
CUSTOMERS_URL = "/api/customers/"
RECEIVABLES_URL = "/api/receivables/"


def days_ago(days):
    return timezone.localdate() - timedelta(days=days)


def at_noon(day):
    return timezone.make_aware(datetime.combine(day, time(12, 0)))


class AnalyticsTestCase(APITestCase):
    def setUp(self):
        cache.clear()
        self.owner_a, self.data_a = make_owner("a@example.com", "A Mart")
        self.owner_b, self.data_b = make_owner("b@example.com", "B Mart")
        self.business_a = Business.objects.get(name="A Mart")
        self.user_a = get_user_model().objects.get(email="a@example.com")
        self.sale_counter = 0
        beverages = self.owner_a.post(CATEGORIES_URL, {"name": "Beverages"}, format="json").data
        self.cola = self.create_product(
            self.owner_a,
            "Cola",
            "COLA",
            "1000.00",
            "600.00",
            "100",
            category=beverages["id"],
        )
        self.water = self.create_product(self.owner_a, "Water", "WATER", "500.00", "300.00", "100")

    # --- helpers -------------------------------------------------------

    def create_product(self, client, name, sku, price, cost, stock, **extra):
        payload = {
            "name": name,
            "sku": sku,
            "selling_price": price,
            "purchase_price": cost,
            "unit": "PIECE",
            "opening_stock": stock,
        }
        payload.update(extra)
        response = client.post(PRODUCTS_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def sell(self, lines, client=None, **extra):
        payload = {
            "items": [{"product": product["id"], "quantity": qty} for product, qty in lines],
            "payment_method": "CASH",
        }
        payload.update(extra)
        response = (client or self.owner_a).post(SALES_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return response.data

    def make_sale(self, day, lines, paid=None, status=SaleStatus.COMPLETED):
        """Record a sale on a past day directly (the API always sells 'now')."""
        self.sale_counter += 1
        total = sum(D(str(qty)) * D(str(price)) for _, qty, price, _ in lines)
        paid = total if paid is None else D(str(paid))
        sale = Sale.objects.create(
            business=self.business_a,
            number=f"T-{self.sale_counter:04d}",
            sold_at=at_noon(day),
            status=status,
            subtotal=total,
            discount=D("0"),
            total=total,
            payment_method="CASH",
            amount_paid=paid,
            outstanding_amount=total - paid,
            created_by=self.user_a,
        )
        for product, qty, price, cost in lines:
            SaleItem.objects.create(
                business=self.business_a,
                sale=sale,
                product_id=product["id"],
                product_name=product["name"],
                sku=product["sku"] or "",
                unit="PIECE",
                quantity=D(str(qty)),
                unit_price=D(str(price)),
                unit_cost=D(str(cost)),
                discount=D("0"),
                line_total=D(str(qty)) * D(str(price)),
            )
        return sale

    def expense(self, category_name, amount, day=None, client=None):
        client = client or self.owner_a
        categories = client.get(EXPENSE_CATEGORIES_URL, {"page_size": 100}).data["results"]
        category = next(c["id"] for c in categories if c["name"] == category_name)
        payload = {
            "description": f"{category_name} expense",
            "category": category,
            "amount": amount,
            "payment_method": "CASH",
        }
        if day:
            payload["expense_date"] = day.isoformat()
        response = client.post(EXPENSES_URL, payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def create_customer(self, name="Mama Rose"):
        return self.owner_a.post(CUSTOMERS_URL, {"name": name}, format="json").data

    def profit(self, client=None, **params):
        response = (client or self.owner_a).get(PROFIT_URL, params or {"period": "today"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def dashboard(self, client=None, **params):
        response = (client or self.owner_a).get(DASHBOARD_URL, params or {"period": "today"})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data


class ProfitCalculationTests(AnalyticsTestCase):
    def test_profit_is_worked_out_from_sales_costs_and_operating_expenses(self):
        self.sell([(self.cola, "3")])  # revenue 3000, cost 1800
        self.sell([(self.water, "2")])  # revenue 1000, cost 600
        self.expense("Rent", "1000.00")  # counts towards profit
        self.expense("Inventory", "5000.00")  # stock purchase: does not
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["revenue"]), D("4000"))
        self.assertEqual(D(figures["cost_of_goods_sold"]), D("2400"))
        self.assertEqual(D(figures["gross_profit"]), D("1600"))
        self.assertEqual(figures["gross_margin_percent"], 40.0)
        self.assertEqual(D(figures["operating_expenses"]), D("1000"))
        self.assertEqual(D(figures["other_spending"]), D("5000"))
        self.assertEqual(D(figures["total_spending"]), D("6000"))
        self.assertEqual(D(figures["estimated_net_profit"]), D("600"))
        self.assertEqual(figures["sales_count"], 2)
        self.assertEqual(D(figures["average_sale"]), D("2000"))

    def test_cancelled_sales_are_left_out(self):
        self.sell([(self.cola, "3")])
        water_sale = self.sell([(self.water, "2")])
        response = self.owner_a.post(
            f"{SALES_URL}{water_sale['id']}/cancel/",
            {"reason": "Mistake"},
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["revenue"]), D("3000"))
        self.assertEqual(D(figures["cost_of_goods_sold"]), D("1800"))
        self.assertEqual(figures["sales_count"], 1)

    def test_a_discount_lowers_revenue_but_not_the_cost_of_the_goods(self):
        self.sell([(self.cola, "1")], discount="100.00")
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["revenue"]), D("900"))
        self.assertEqual(D(figures["cost_of_goods_sold"]), D("600"))
        self.assertEqual(D(figures["gross_profit"]), D("300"))

    def test_credit_sales_count_as_revenue_but_are_shown_separately(self):
        customer = self.create_customer()
        self.sell([(self.cola, "1")], payment_method="CREDIT", customer=customer["id"])
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["revenue"]), D("1000"))
        self.assertEqual(D(figures["credit_sales"]), D("1000"))

    def test_changing_a_cost_price_later_does_not_rewrite_history(self):
        self.sell([(self.cola, "1")])
        self.owner_a.patch(
            f"{PRODUCTS_URL}{self.cola['id']}/",
            {"purchase_price": "900.00"},
            format="json",
        )
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["cost_of_goods_sold"]), D("600"))

    def test_a_business_with_no_activity_gets_zeros_not_errors(self):
        data = self.profit(client=self.owner_b, period="this_month")
        figures = data["figures"]
        self.assertEqual(D(figures["revenue"]), D("0"))
        self.assertEqual(D(figures["estimated_net_profit"]), D("0"))
        self.assertIsNone(figures["gross_margin_percent"])
        self.assertIsNone(figures["average_sale"])
        self.assertEqual(set(data["changes"].values()), {None})
        self.assertGreaterEqual(len(data["daily"]), 1)

    def test_other_businesses_data_is_never_included(self):
        theirs = self.create_product(self.owner_b, "Tea", "TEA", "200.00", "100.00", "10")
        self.sell([(theirs, "2")], client=self.owner_b)
        self.expense("Rent", "500.00", client=self.owner_b)
        figures = self.profit(period="today")["figures"]
        self.assertEqual(D(figures["revenue"]), D("0"))
        self.assertEqual(D(figures["total_spending"]), D("0"))

    def test_daily_series_has_one_entry_per_day_in_order(self):
        self.sell([(self.cola, "1")])
        daily = self.profit(period="last_7_days")["daily"]
        self.assertEqual(len(daily), 7)
        self.assertEqual([d["date"] for d in daily], sorted(d["date"] for d in daily))
        self.assertEqual(daily[-1]["date"], timezone.localdate().isoformat())
        self.assertEqual(D(daily[-1]["revenue"]), D("1000"))
        self.assertEqual(D(daily[0]["revenue"]), D("0"))

    def test_custom_date_range(self):
        self.make_sale(days_ago(10), [(self.cola, 1, 1000, 600)])
        data = self.profit(date_from=days_ago(12).isoformat(), date_to=days_ago(8).isoformat())
        self.assertEqual(data["period"]["name"], "custom")
        self.assertEqual(data["period"]["days"], 5)
        self.assertEqual(D(data["figures"]["revenue"]), D("1000"))

    def test_bad_period_inputs_are_refused(self):
        today = timezone.localdate().isoformat()
        bad_requests = [
            {"period": "forever"},
            {"date_from": today},
            {"period": "today", "date_from": today, "date_to": today},
            {"date_from": today, "date_to": days_ago(3).isoformat()},
            {"date_from": days_ago(400).isoformat(), "date_to": today},
            {"date_from": "not-a-date", "date_to": today},
        ]
        for params in bad_requests:
            response = self.owner_a.get(PROFIT_URL, params)
            self.assertEqual(response.status_code, 400, params)

    def test_only_owners_and_managers_can_see_profit(self):
        staff = make_member_client(self.owner_a, "staff@example.com", "STAFF")
        manager = make_member_client(self.owner_a, "manager@example.com", "MANAGER")
        self.assertEqual(staff.get(PROFIT_URL).status_code, 403)
        self.assertEqual(staff.get(DASHBOARD_URL).status_code, 403)
        self.assertEqual(manager.get(PROFIT_URL).status_code, 200)
        self.assertEqual(manager.get(DASHBOARD_URL).status_code, 200)
        self.assertEqual(APIClient().get(PROFIT_URL).status_code, 401)
        self.assertEqual(APIClient().get(DASHBOARD_URL).status_code, 401)


class PeriodComparisonTests(AnalyticsTestCase):
    def test_changes_compare_with_the_previous_period(self):
        self.make_sale(days_ago(10), [(self.cola, 1, 1000, 600)])  # previous 7 days
        self.make_sale(days_ago(1), [(self.cola, 1, 1180, 600)])  # last 7 days
        data = self.profit(period="last_7_days")
        self.assertEqual(D(data["previous"]["revenue"]), D("1000"))
        self.assertEqual(D(data["figures"]["revenue"]), D("1180"))
        self.assertEqual(data["changes"]["revenue"], 18.0)

    def test_nothing_to_compare_gives_no_percentage(self):
        self.make_sale(days_ago(1), [(self.cola, 1, 1000, 600)])
        self.assertIsNone(self.profit(period="last_7_days")["changes"]["revenue"])


class DashboardTests(AnalyticsTestCase):
    def test_dashboard_has_everything_the_screen_needs(self):
        data = self.dashboard(period="this_month")
        expected = {
            "generated_at",
            "currency",
            "period",
            "today",
            "figures",
            "previous",
            "changes",
            "daily",
            "top_products",
            "sales_by_category",
            "receivables",
            "inventory",
            "insights",
        }
        self.assertTrue(expected <= set(data))
        self.assertEqual(data["currency"], "SSP")

    def test_todays_sales_and_spending(self):
        self.sell([(self.cola, "3")])
        self.sell([(self.water, "2")])
        self.expense("Rent", "1000.00")
        self.expense("Inventory", "5000.00")
        today = self.dashboard(period="last_30_days")["today"]
        self.assertEqual(D(today["sales_total"]), D("4000"))
        self.assertEqual(today["sales_count"], 2)
        self.assertEqual(D(today["total_spending"]), D("6000"))

    def test_top_products_and_categories(self):
        self.sell([(self.cola, "3")])
        self.sell([(self.water, "2")])
        data = self.dashboard(period="today")
        top = data["top_products"]
        self.assertEqual([p["name"] for p in top], ["Cola", "Water"])
        self.assertEqual(D(top[0]["revenue"]), D("3000"))
        self.assertEqual(D(top[0]["profit"]), D("1200"))
        categories = data["sales_by_category"]
        self.assertEqual([c["category"] for c in categories], ["Beverages", None])
        self.assertEqual(D(categories[0]["revenue"]), D("3000"))

    def test_customer_debt(self):
        customer = self.create_customer()
        self.sell([(self.cola, "1")], payment_method="CREDIT", customer=customer["id"])
        response = self.owner_a.post(
            RECEIVABLES_URL,
            {
                "customer": customer["id"],
                "original_amount": "500.00",
                "issue_date": days_ago(20).isoformat(),
                "due_date": days_ago(1).isoformat(),
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.data)
        receivables = self.dashboard()["receivables"]
        self.assertEqual(D(receivables["outstanding"]), D("1500"))
        self.assertEqual(D(receivables["overdue_amount"]), D("500"))
        self.assertEqual(receivables["overdue_customers"], 1)

    def test_inventory_value_and_stock_alerts(self):
        self.create_product(
            self.owner_a,
            "Soap",
            "SOAP",
            "300.00",
            "100.00",
            "5",
            min_stock_threshold="10",
        )
        self.create_product(self.owner_a, "Tea", "TEA", "200.00", "50.00", "0")
        retired = self.create_product(self.owner_a, "Old", "OLD", "100.00", "100.00", "10")
        self.owner_a.patch(f"{PRODUCTS_URL}{retired['id']}/", {"is_active": False}, format="json")

        inventory = self.dashboard()["inventory"]
        # Cola 100 x 600 + Water 100 x 300 + Soap 5 x 100 (inactive products don't count)
        self.assertEqual(D(inventory["value"]), D("90500"))
        self.assertEqual(inventory["low_stock_count"], 1)
        self.assertEqual(inventory["out_of_stock_count"], 1)
        self.assertEqual(
            [(p["name"], p["status"]) for p in inventory["needs_restock"]],
            [("Tea", "out"), ("Soap", "low")],
        )

    def test_insights_for_stock_and_debt(self):
        self.create_product(
            self.owner_a,
            "Soap",
            "SOAP",
            "300.00",
            "100.00",
            "5",
            min_stock_threshold="10",
        )
        self.create_product(self.owner_a, "Tea", "TEA", "200.00", "50.00", "0")
        customer = self.create_customer()
        self.owner_a.post(
            RECEIVABLES_URL,
            {
                "customer": customer["id"],
                "original_amount": "500.00",
                "issue_date": days_ago(20).isoformat(),
                "due_date": days_ago(1).isoformat(),
            },
            format="json",
        )
        insights = self.dashboard()["insights"]
        by_type = {(i["type"], i["severity"]): i["message"] for i in insights}
        self.assertEqual(by_type[("inventory", "CRITICAL")], "1 product is out of stock.")
        self.assertEqual(
            by_type[("inventory", "WARNING")],
            "Soap has fallen below its minimum stock level.",
        )
        self.assertEqual(
            by_type[("debt", "WARNING")],
            "1 customer has an overdue balance of 500 SSP.",
        )
        self.assertEqual(insights[0]["severity"], "CRITICAL")

    def test_expenses_growing_faster_than_sales_and_profit_falling(self):
        self.make_sale(days_ago(10), [(self.cola, 1, 1000, 600)])  # previous 7 days
        self.make_sale(days_ago(1), [(self.cola, 1, 1080, 600)])  # last 7 days
        self.expense("Rent", "1000.00", day=days_ago(10))
        self.expense("Rent", "1310.00")
        messages = [i["message"] for i in self.dashboard(period="last_7_days")["insights"]]
        self.assertTrue(
            any("Expenses increased 31% while sales increased only 8%" in m for m in messages),
            messages,
        )
        self.assertIn("Revenue increased but estimated profit declined.", messages)

    def test_sales_increase_insight(self):
        self.make_sale(days_ago(10), [(self.cola, 1, 1000, 600)])
        self.make_sale(days_ago(1), [(self.cola, 1, 1180, 600)])
        messages = [i["message"] for i in self.dashboard(period="last_7_days")["insights"]]
        self.assertIn("Sales increased 18% compared with the previous 7 days.", messages)

    def test_today_is_not_compared_with_a_whole_yesterday(self):
        self.make_sale(days_ago(1), [(self.cola, 10, 1000, 600)])
        self.sell([(self.cola, "1")])
        types = [i["type"] for i in self.dashboard(period="today")["insights"]]
        self.assertNotIn("expenses", types)
        messages = [i["message"] for i in self.dashboard(period="today")["insights"]]
        self.assertFalse(any(m.startswith("Sales decreased") for m in messages))

    def test_growing_customer_debt_is_noticed(self):
        customer = self.create_customer()
        old = self.owner_a.post(
            RECEIVABLES_URL,
            {"customer": customer["id"], "original_amount": "1000.00"},
            format="json",
        ).data
        Receivable.objects.filter(pk=old["id"]).update(created_at=at_noon(days_ago(10)))
        self.owner_a.post(
            RECEIVABLES_URL,
            {"customer": customer["id"], "original_amount": "200.00"},
            format="json",
        )
        messages = [i["message"] for i in self.dashboard(period="last_7_days")["insights"]]
        self.assertTrue(
            any("Customer receivables increased by 20%" in m for m in messages),
            messages,
        )

    def test_an_empty_business_gets_an_empty_dashboard(self):
        data = self.dashboard(client=self.owner_b, period="this_month")
        self.assertEqual(data["insights"], [])
        self.assertEqual(data["top_products"], [])
        self.assertEqual(D(data["inventory"]["value"]), D("0"))
        self.assertEqual(D(data["receivables"]["outstanding"]), D("0"))

    def test_dashboard_is_isolated_between_businesses(self):
        self.sell([(self.cola, "3")])
        data = self.dashboard(client=self.owner_b, period="today")
        self.assertEqual(D(data["figures"]["revenue"]), D("0"))
        self.assertEqual(data["top_products"], [])
        self.assertEqual(data["inventory"]["needs_restock"], [])

    def test_dashboard_stays_cheap(self):
        self.sell([(self.cola, "1")])
        with CaptureQueriesContext(connection) as queries:
            self.dashboard(period="this_month")
        self.assertLess(len(queries), 45)
