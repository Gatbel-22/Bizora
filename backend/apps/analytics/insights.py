from dataclasses import dataclass
from decimal import Decimal

from apps.core.money import quantize_money

from .calculations import percent_change

SEVERITY_ORDER = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}

COMPARE_LABELS = {
    "today": "yesterday",
    "last_7_days": "the previous 7 days",
    "this_month": "the same days last month",
    "last_30_days": "the previous 30 days",
    "last_month": "the month before",
}


@dataclass(frozen=True)
class Insight:
    type: str  # sales, expenses, profit, inventory, debt, cash
    severity: str  # INFO, WARNING or CRITICAL
    title: str
    message: str
    metric: dict | None = None
    related: dict | None = None  # where the app can send the user: {"type": "products"}

    def as_dict(self):
        return {
            "type": self.type,
            "severity": self.severity,
            "title": self.title,
            "message": self.message,
            "metric": self.metric,
            "related": self.related,
        }


@dataclass
class InsightContext:
    """Everything the rules are allowed to look at."""

    currency: str
    period: object
    current: object  # Figures for this period
    previous: object  # Figures for the comparison period
    changes: dict  # percent changes (None when there's nothing to compare)
    receivables: dict
    receivables_at_start: Decimal
    inventory: dict
    top_products: list


def format_amount(amount, currency):
    amount = quantize_money(amount, currency)
    if amount == amount.to_integral_value():
        return f"{int(amount):,} {currency}"
    return f"{amount:,.2f} {currency}"


def _label(ctx):
    return COMPARE_LABELS.get(ctx.period.name, "the previous period")


def _is_today(ctx):
    # A part-finished day can't be fairly compared with a whole one.
    return ctx.period.name == "today"


def sales_trend_rule(ctx):
    change = ctx.changes["revenue"]
    if _is_today(ctx) or change is None:
        return []
    metric = {"name": "sales_change_percent", "value": change}
    if change >= 10:
        message = f"Sales increased {change:g}% compared with {_label(ctx)}."
        return [Insight("sales", "INFO", "Sales are up", message, metric, {"type": "sales"})]
    if change <= -10:
        severity = "CRITICAL" if change <= -30 else "WARNING"
        message = f"Sales decreased {abs(change):g}% compared with {_label(ctx)}."
        return [Insight("sales", severity, "Sales are down", message, metric, {"type": "sales"})]
    return []


def expenses_vs_sales_rule(ctx):
    expenses, sales = ctx.changes["operating_expenses"], ctx.changes["revenue"]
    if _is_today(ctx) or expenses is None or expenses < 20:
        return []
    if sales is not None and sales >= expenses - 10:
        return []  # sales kept pace with spending
    if sales is None:
        message = f"Expenses increased {expenses:g}% compared with {_label(ctx)}."
    elif sales >= 0:
        message = (
            f"Expenses increased {expenses:g}% while sales increased only {sales:g}% "
            f"compared with {_label(ctx)}."
        )
    else:
        message = (
            f"Expenses increased {expenses:g}% while sales decreased {abs(sales):g}% "
            f"compared with {_label(ctx)}."
        )
    metric = {"name": "expense_change_percent", "value": expenses}
    return [
        Insight(
            "expenses",
            "WARNING",
            "Expenses are growing",
            message,
            metric,
            {"type": "expenses"},
        )
    ]


def profit_rule(ctx):
    insights = []
    current, previous = ctx.current, ctx.previous
    if current.revenue > 0 and current.net_profit < 0:
        loss = format_amount(abs(current.net_profit), ctx.currency)
        insights.append(
            Insight(
                "profit",
                "WARNING",
                "Estimated loss",
                f"Your estimated profit is negative: expenses are {loss} higher than "
                "your gross profit in this period.",
                {"name": "estimated_net_profit", "value": str(current.net_profit)},
                {"type": "expenses"},
            )
        )
    revenue_change = ctx.changes["revenue"]
    if (
        not _is_today(ctx)
        and revenue_change is not None
        and revenue_change > 0
        and current.net_profit < previous.net_profit
    ):
        insights.append(
            Insight(
                "profit",
                "WARNING",
                "Profit fell even though sales grew",
                "Revenue increased but estimated profit declined.",
                {"name": "estimated_net_profit", "value": str(current.net_profit)},
                {"type": "expenses"},
            )
        )
    return insights


def margin_rule(ctx):
    now, before = ctx.current.gross_margin_percent, ctx.previous.gross_margin_percent
    if _is_today(ctx) or now is None or before is None or before - now < 5:
        return []
    message = (
        f"Your gross margin fell from {before:g}% to {now:g}%. "
        "Check your selling prices and what your suppliers charge."
    )
    metric = {"name": "gross_margin_percent", "value": now}
    return [
        Insight(
            "profit",
            "WARNING",
            "Margins are shrinking",
            message,
            metric,
            {"type": "products"},
        )
    ]


def inventory_rule(ctx):
    inventory = ctx.inventory
    insights = []
    out = inventory["out_of_stock_count"]
    low = inventory["low_stock_count"]
    if out:
        verb = "product is" if out == 1 else "products are"
        insights.append(
            Insight(
                "inventory",
                "CRITICAL",
                "Out of stock",
                f"{out} {verb} out of stock.",
                {"name": "out_of_stock_count", "value": out},
                {"type": "products"},
            )
        )
    if low:
        low_items = [item for item in inventory["needs_restock"] if item["status"] == "low"]
        if low == 1 and len(low_items) == 1:
            message = f"{low_items[0]['name']} has fallen below its minimum stock level."
        else:
            message = f"{low} products are low in stock."
        insights.append(
            Insight(
                "inventory",
                "WARNING",
                "Low stock",
                message,
                {"name": "low_stock_count", "value": low},
                {"type": "products"},
            )
        )
    return insights


def debt_rule(ctx):
    insights = []
    receivables = ctx.receivables
    count = receivables["overdue_customers"]
    if count:
        amount = format_amount(receivables["overdue_amount"], ctx.currency)
        if count == 1:
            message = f"1 customer has an overdue balance of {amount}."
        else:
            message = f"{count} customers have overdue balances totaling {amount}."
        insights.append(
            Insight(
                "debt",
                "WARNING",
                "Overdue customer debts",
                message,
                {"name": "overdue_amount", "value": str(receivables["overdue_amount"])},
                {"type": "customers"},
            )
        )
    growth = percent_change(receivables["outstanding"], ctx.receivables_at_start)
    if not _is_today(ctx) and growth is not None and growth >= 10:
        severity = "WARNING" if growth >= 25 else "INFO"
        insights.append(
            Insight(
                "debt",
                severity,
                "Customer debt is growing",
                f"Customer receivables increased by {growth:g}% since the start of this period.",
                {"name": "receivables_change_percent", "value": growth},
                {"type": "customers"},
            )
        )
    return insights


def credit_share_rule(ctx):
    current = ctx.current
    if current.revenue <= 0:
        return []
    share = current.credit_sales / current.revenue
    if share < Decimal("0.3"):
        return []
    amount = format_amount(current.credit_sales, ctx.currency)
    message = (
        f"{share * 100:.0f}% of sales ({amount}) were sold on credit, "
        "so that money isn't in your hands yet."
    )
    metric = {"name": "credit_share_percent", "value": round(float(share * 100), 1)}
    return [
        Insight(
            "cash",
            "INFO",
            "Many sales on credit",
            message,
            metric,
            {"type": "customers"},
        )
    ]


def top_product_rule(ctx):
    if not ctx.top_products:
        return []
    best = ctx.top_products[0]
    amount = format_amount(best["revenue"], ctx.currency)
    message = f"{best['name']} is your top seller in this period, bringing in {amount}."
    return [Insight("sales", "INFO", "Top seller", message, None, {"type": "products"})]


DEFAULT_RULES = (
    sales_trend_rule,
    expenses_vs_sales_rule,
    profit_rule,
    margin_rule,
    inventory_rule,
    debt_rule,
    credit_share_rule,
    top_product_rule,
)


class InsightEngine:
    """Runs a set of rules and returns the most important insights first.

    Today every rule is plain arithmetic. Statistical or AI-written insights can be added
    later as extra rules (or a different engine) without changing the dashboard.
    """

    def __init__(self, rules=DEFAULT_RULES):
        self.rules = rules

    def generate(self, context):
        insights = []
        for rule in self.rules:
            insights.extend(rule(context))
        return sorted(insights, key=lambda insight: SEVERITY_ORDER[insight.severity])
