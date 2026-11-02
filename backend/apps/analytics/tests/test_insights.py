from datetime import date
from decimal import Decimal as D

from django.test import SimpleTestCase

from apps.analytics.calculations import Figures
from apps.analytics.insights import InsightContext, InsightEngine
from apps.analytics.periods import resolve_period


def figures(revenue=0, cogs=0, operating=0, excluded=0, credit=0, count=0):
    return Figures(
        revenue=D(revenue),
        cogs=D(cogs),
        operating_expenses=D(operating),
        excluded_expenses=D(excluded),
        credit_sales=D(credit),
        sales_count=count,
    )


def context(
    period="this_month",
    current=None,
    previous=None,
    changes=None,
    receivables=None,
    receivables_at_start=0,
    inventory=None,
    top_products=None,
):
    all_changes = {
        "revenue": None,
        "gross_profit": None,
        "operating_expenses": None,
        "total_spending": None,
        "estimated_net_profit": None,
    }
    all_changes.update(changes or {})
    return InsightContext(
        currency="SSP",
        period=resolve_period(period, today=date(2026, 10, 14)),
        current=current or figures(),
        previous=previous or figures(),
        changes=all_changes,
        receivables=receivables
        or {"outstanding": D(0), "overdue_amount": D(0), "overdue_customers": 0},
        receivables_at_start=D(receivables_at_start),
        inventory=inventory
        or {"low_stock_count": 0, "out_of_stock_count": 0, "needs_restock": []},
        top_products=top_products or [],
    )


def run(**kwargs):
    return InsightEngine().generate(context(**kwargs))


def messages(**kwargs):
    return [insight.message for insight in run(**kwargs)]


class InsightRuleTests(SimpleTestCase):
    def test_nothing_to_say_when_there_is_no_data(self):
        self.assertEqual(run(), [])

    def test_sales_increase(self):
        insights = run(changes={"revenue": 18.0})
        self.assertEqual(insights[0].severity, "INFO")
        self.assertEqual(
            insights[0].message,
            "Sales increased 18% compared with the same days last month.",
        )

    def test_small_sales_changes_are_ignored(self):
        self.assertEqual(run(changes={"revenue": 5.0}), [])
        self.assertEqual(run(changes={"revenue": -5.0}), [])

    def test_sales_decline_severity_grows_with_the_drop(self):
        self.assertEqual(run(changes={"revenue": -12.0})[0].severity, "WARNING")
        self.assertEqual(run(changes={"revenue": -35.0})[0].severity, "CRITICAL")

    def test_part_finished_days_are_not_compared(self):
        self.assertEqual(run(period="today", changes={"revenue": -50.0}), [])

    def test_expenses_growing_faster_than_sales(self):
        result = messages(changes={"revenue": 8.0, "operating_expenses": 31.0})
        self.assertIn(
            "Expenses increased 31% while sales increased only 8% "
            "compared with the same days last month.",
            result,
        )

    def test_no_warning_when_sales_keep_pace(self):
        self.assertEqual(
            [
                m
                for m in messages(changes={"revenue": 40.0, "operating_expenses": 31.0})
                if "Expenses" in m
            ],
            [],
        )

    def test_expenses_up_while_sales_fall(self):
        result = messages(changes={"revenue": -5.0, "operating_expenses": 31.0})
        self.assertTrue(any("while sales decreased 5%" in m for m in result))

    def test_expenses_up_with_no_sales_to_compare(self):
        result = messages(changes={"operating_expenses": 31.0})
        self.assertTrue(any(m.startswith("Expenses increased 31%") for m in result))

    def test_profit_fell_even_though_revenue_grew(self):
        result = messages(
            current=figures(revenue=1080, cogs=600, operating=1310),
            previous=figures(revenue=1000, cogs=600, operating=1000),
            changes={"revenue": 8.0},
        )
        self.assertIn("Revenue increased but estimated profit declined.", result)

    def test_estimated_loss_is_flagged(self):
        insights = run(current=figures(revenue=1000, cogs=600, operating=700))
        loss = [i for i in insights if i.title == "Estimated loss"]
        self.assertEqual(len(loss), 1)
        self.assertIn("300 SSP", loss[0].message)

    def test_shrinking_margin(self):
        result = messages(
            current=figures(revenue=1000, cogs=750),
            previous=figures(revenue=1000, cogs=680),
        )
        self.assertTrue(any("gross margin fell from 32% to 25%" in m for m in result))

    def test_out_of_stock_products(self):
        inventory = {"low_stock_count": 0, "out_of_stock_count": 3, "needs_restock": []}
        insights = run(inventory=inventory)
        self.assertEqual(insights[0].severity, "CRITICAL")
        self.assertEqual(insights[0].message, "3 products are out of stock.")
        inventory["out_of_stock_count"] = 1
        self.assertEqual(
            run(inventory=inventory)[0].message, "1 product is out of stock."
        )

    def test_a_single_low_product_is_named(self):
        inventory = {
            "low_stock_count": 1,
            "out_of_stock_count": 0,
            "needs_restock": [{"name": "Soap", "status": "low"}],
        }
        self.assertEqual(
            run(inventory=inventory)[0].message,
            "Soap has fallen below its minimum stock level.",
        )

    def test_several_low_products(self):
        inventory = {"low_stock_count": 7, "out_of_stock_count": 0, "needs_restock": []}
        self.assertEqual(
            run(inventory=inventory)[0].message, "7 products are low in stock."
        )

    def test_overdue_customers(self):
        receivables = {
            "outstanding": D(3000000),
            "overdue_amount": D(1850000),
            "overdue_customers": 3,
        }
        self.assertIn(
            "3 customers have overdue balances totaling 1,850,000 SSP.",
            messages(receivables=receivables),
        )
        receivables["overdue_customers"] = 1
        receivables["overdue_amount"] = D(500000)
        self.assertIn(
            "1 customer has an overdue balance of 500,000 SSP.",
            messages(receivables=receivables),
        )

    def test_growing_receivables(self):
        receivables = {
            "outstanding": D(1150),
            "overdue_amount": D(0),
            "overdue_customers": 0,
        }
        insights = run(receivables=receivables, receivables_at_start=1000)
        self.assertEqual(insights[0].severity, "INFO")
        self.assertIn("Customer receivables increased by 15%", insights[0].message)
        receivables["outstanding"] = D(1300)
        self.assertEqual(
            run(receivables=receivables, receivables_at_start=1000)[0].severity,
            "WARNING",
        )

    def test_a_large_share_of_credit_sales(self):
        result = messages(current=figures(revenue=1000, credit=400))
        self.assertTrue(
            any("40% of sales (400 SSP) were sold on credit" in m for m in result)
        )

    def test_top_seller(self):
        top = [{"name": "Cola", "revenue": D(120000)}]
        self.assertIn(
            "Cola is your top seller in this period, bringing in 120,000 SSP.",
            messages(top_products=top),
        )

    def test_most_important_insights_come_first(self):
        insights = run(
            changes={"revenue": 20.0},
            inventory={
                "low_stock_count": 2,
                "out_of_stock_count": 1,
                "needs_restock": [],
            },
            receivables={
                "outstanding": D(10),
                "overdue_amount": D(10),
                "overdue_customers": 1,
            },
        )
        self.assertEqual(insights[0].severity, "CRITICAL")
        self.assertEqual(insights[-1].severity, "INFO")
