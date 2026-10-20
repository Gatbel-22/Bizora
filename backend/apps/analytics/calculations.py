from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, ExpressionWrapper, F, Max, Q, Sum
from django.db.models.functions import TruncDate

from apps.core.money import MONEY_DECIMAL_PLACES, MONEY_MAX_DIGITS, quantize_money
from apps.customers.models import PaymentAllocation, Receivable
from apps.expenses.models import Expense
from apps.inventory.models import Product
from apps.sales.models import Sale, SaleItem, SaleStatus

from .periods import day_bounds

ZERO = Decimal("0")
MONEY = DecimalField(max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
PRECISE = DecimalField(max_digits=30, decimal_places=5)

# What a sold line cost us: the cost saved on the line at the time of the sale.
COST_OF_LINE = ExpressionWrapper(F("unit_cost") * F("quantity"), output_field=PRECISE)


@dataclass(frozen=True)
class Figures:
    """The money picture for one day or one period."""

    revenue: Decimal = ZERO
    cogs: Decimal = ZERO  # cost of goods sold
    operating_expenses: Decimal = ZERO  # expenses that count towards profit
    excluded_expenses: Decimal = ZERO  # spending that doesn't (e.g. stock purchases)
    credit_sales: Decimal = ZERO  # part of revenue sold on credit
    sales_count: int = 0

    @property
    def gross_profit(self):
        return self.revenue - self.cogs

    @property
    def net_profit(self):
        return self.gross_profit - self.operating_expenses

    @property
    def total_spending(self):
        return self.operating_expenses + self.excluded_expenses

    @property
    def gross_margin_percent(self):
        if self.revenue <= 0:
            return None
        return round(float(self.gross_profit / self.revenue * 100), 1)

    @property
    def average_sale(self):
        if not self.sales_count:
            return None
        return self.revenue / self.sales_count


def sum_figures(items):
    items = list(items)
    return Figures(
        revenue=sum((i.revenue for i in items), ZERO),
        cogs=sum((i.cogs for i in items), ZERO),
        operating_expenses=sum((i.operating_expenses for i in items), ZERO),
        excluded_expenses=sum((i.excluded_expenses for i in items), ZERO),
        credit_sales=sum((i.credit_sales for i in items), ZERO),
        sales_count=sum(i.sales_count for i in items),
    )


def percent_change(current, previous):
    """How much `current` moved from `previous`, in percent (None if nothing to compare)."""
    if not previous:
        return None
    return round(float((current - previous) / abs(previous) * 100), 1)


def daily_figures(business, start, end):
    """One Figures per day from start to end (days with no activity are zero)."""
    lower, upper = day_bounds(start, end)
    currency = business.currency

    buckets = {}
    day = start
    while day <= end:
        buckets[day] = {
            "revenue": ZERO,
            "cogs": ZERO,
            "operating": ZERO,
            "excluded": ZERO,
            "credit": ZERO,
            "count": 0,
        }
        day += timedelta(days=1)

    completed_sales = Sale.objects.filter(
        business=business,
        status=SaleStatus.COMPLETED,
        sold_at__gte=lower,
        sold_at__lt=upper,
    )
    sales = (
        completed_sales.annotate(day=TruncDate("sold_at"))
        .values("day")
        .annotate(revenue=Sum("total"), credit=Sum("outstanding_amount"), count=Count("id"))
        .order_by()
    )
    for row in sales:
        bucket = buckets.get(row["day"])
        if bucket is not None:
            bucket["revenue"] = row["revenue"]
            bucket["credit"] = row["credit"]
            bucket["count"] = row["count"]

    lines = SaleItem.objects.filter(
        business=business,
        sale__status=SaleStatus.COMPLETED,
        sale__sold_at__gte=lower,
        sale__sold_at__lt=upper,
    )
    costs = (
        lines.annotate(day=TruncDate("sale__sold_at"))
        .values("day")
        .annotate(cogs=Sum(COST_OF_LINE))
        .order_by()
    )
    for row in costs:
        bucket = buckets.get(row["day"])
        if bucket is not None:
            bucket["cogs"] = quantize_money(row["cogs"], currency)

    expenses = (
        Expense.objects.filter(business=business, expense_date__gte=start, expense_date__lte=end)
        .values("expense_date", "category__affects_profit")
        .annotate(total=Sum("amount"))
        .order_by()
    )
    for row in expenses:
        bucket = buckets.get(row["expense_date"])
        if bucket is not None:
            key = "operating" if row["category__affects_profit"] else "excluded"
            bucket[key] += row["total"]

    return {
        day: Figures(
            revenue=b["revenue"],
            cogs=b["cogs"],
            operating_expenses=b["operating"],
            excluded_expenses=b["excluded"],
            credit_sales=b["credit"],
            sales_count=b["count"],
        )
        for day, b in buckets.items()
    }


def top_products(business, start, end, limit=5):
    """Best sellers by revenue. (Line revenue, before any whole-sale discount.)"""
    lower, upper = day_bounds(start, end)
    currency = business.currency
    rows = (
        SaleItem.objects.filter(
            business=business,
            sale__status=SaleStatus.COMPLETED,
            sale__sold_at__gte=lower,
            sale__sold_at__lt=upper,
        )
        .values("product_id")
        .annotate(
            name=Max("product_name"),
            # Not called "quantity": that is a column the cost calculation below needs.
            units=Sum("quantity"),
            revenue=Sum("line_total"),
            cost=Sum(COST_OF_LINE),
        )
        .order_by("-revenue")[:limit]
    )
    return [
        {
            "product": row["product_id"],
            "name": row["name"],
            "quantity": row["units"],
            "revenue": row["revenue"],
            "profit": row["revenue"] - quantize_money(row["cost"], currency),
        }
        for row in rows
    ]


def sales_by_category(business, start, end, limit=8):
    lower, upper = day_bounds(start, end)
    rows = (
        SaleItem.objects.filter(
            business=business,
            sale__status=SaleStatus.COMPLETED,
            sale__sold_at__gte=lower,
            sale__sold_at__lt=upper,
        )
        .values("product__category__name")
        .annotate(revenue=Sum("line_total"))
        .order_by("-revenue")[:limit]
    )
    return [{"category": row["product__category__name"], "revenue": row["revenue"]} for row in rows]


def receivables_snapshot(business, today):
    """What customers owe right now, and how much of it is late."""
    owed = ExpressionWrapper(F("original_amount") - F("amount_paid"), output_field=MONEY)
    open_debts = Receivable.objects.filter(business=business).open()
    outstanding = open_debts.aggregate(total=Sum(owed))["total"] or ZERO
    overdue = open_debts.filter(due_date__lt=today).aggregate(
        total=Sum(owed), customers=Count("customer", distinct=True)
    )
    return {
        "outstanding": outstanding,
        "overdue_amount": overdue["total"] or ZERO,
        "overdue_customers": overdue["customers"] or 0,
    }


def receivables_outstanding_on(business, day):
    """What customers owed at the end of `day`, from when debts and payments were recorded."""
    _, upper = day_bounds(day, day)
    debts = (
        Receivable.objects.filter(business=business, created_at__lt=upper)
        .filter(Q(voided_at__isnull=True) | Q(voided_at__gte=upper))
        .aggregate(total=Sum("original_amount"))["total"]
        or ZERO
    )
    paid = (
        PaymentAllocation.objects.filter(
            payment__business=business, created_at__lt=upper
        ).aggregate(total=Sum("amount"))["total"]
        or ZERO
    )
    return debts - paid


def inventory_snapshot(business, limit=5):
    """Stock on hand valued at cost, plus which active products need restocking."""
    active = Product.objects.filter(business=business, is_active=True)
    value = (
        active.aggregate(
            total=Sum(
                ExpressionWrapper(F("current_stock") * F("purchase_price"), output_field=PRECISE)
            )
        )["total"]
        or ZERO
    )
    needs = active.filter(current_stock__lte=F("min_stock_threshold")).order_by(
        "current_stock", "name"
    )
    restock = [
        {
            "id": row["id"],
            "name": row["name"],
            "current_stock": row["current_stock"],
            "min_stock_threshold": row["min_stock_threshold"],
            "unit": row["unit"],
            "status": "out" if row["current_stock"] <= 0 else "low",
        }
        for row in needs.values("id", "name", "current_stock", "min_stock_threshold", "unit")[
            :limit
        ]
    ]
    return {
        "value": quantize_money(value, business.currency),
        "low_stock_count": active.low_stock().count(),
        "out_of_stock_count": active.out_of_stock().count(),
        "needs_restock": restock,
    }
