from datetime import timedelta

from django.utils import timezone

from apps.core.money import quantize_money

from . import calculations as calc
from .insights import InsightContext, InsightEngine


def _period_dict(period):
    return {
        "name": period.name,
        "start": period.start.isoformat(),
        "end": period.end.isoformat(),
        "previous_start": period.previous_start.isoformat(),
        "previous_end": period.previous_end.isoformat(),
        "days": period.days,
    }


def _figures_dict(figures, currency):
    def money(value):
        return quantize_money(value, currency)

    average = figures.average_sale
    return {
        "revenue": money(figures.revenue),
        "cost_of_goods_sold": money(figures.cogs),
        "gross_profit": money(figures.gross_profit),
        "gross_margin_percent": figures.gross_margin_percent,
        "operating_expenses": money(figures.operating_expenses),
        "other_spending": money(figures.excluded_expenses),
        "total_spending": money(figures.total_spending),
        "estimated_net_profit": money(figures.net_profit),
        "credit_sales": money(figures.credit_sales),
        "sales_count": figures.sales_count,
        "average_sale": money(average) if average is not None else None,
    }


def _changes_dict(current, previous):
    return {
        "revenue": calc.percent_change(current.revenue, previous.revenue),
        "gross_profit": calc.percent_change(current.gross_profit, previous.gross_profit),
        "operating_expenses": calc.percent_change(
            current.operating_expenses, previous.operating_expenses
        ),
        "total_spending": calc.percent_change(current.total_spending, previous.total_spending),
        "estimated_net_profit": calc.percent_change(current.net_profit, previous.net_profit),
    }


def _daily_list(days, currency):
    def money(value):
        return quantize_money(value, currency)

    return [
        {
            "date": day.isoformat(),
            "revenue": money(figures.revenue),
            "gross_profit": money(figures.gross_profit),
            "operating_expenses": money(figures.operating_expenses),
            "total_spending": money(figures.total_spending),
            "net_profit": money(figures.net_profit),
        }
        for day, figures in sorted(days.items())
    ]


def build_profit_report(business, period):
    """Revenue, costs and estimated profit for a period, compared with the one before it."""
    currency = business.currency
    days = calc.daily_figures(business, period.start, period.end)
    current = calc.sum_figures(days.values())
    previous_days = calc.daily_figures(business, period.previous_start, period.previous_end)
    previous = calc.sum_figures(previous_days.values())
    return {
        "currency": currency,
        "period": _period_dict(period),
        "figures": _figures_dict(current, currency),
        "previous": _figures_dict(previous, currency),
        "changes": _changes_dict(current, previous),
        "daily": _daily_list(days, currency),
    }


def build_dashboard(business, period):
    """Everything the dashboard shows, worked out in one place."""
    currency = business.currency
    today = timezone.localdate()

    days = calc.daily_figures(business, period.start, period.end)
    current = calc.sum_figures(days.values())
    previous_days = calc.daily_figures(business, period.previous_start, period.previous_end)
    previous = calc.sum_figures(previous_days.values())
    changes = _changes_dict(current, previous)

    today_figures = days.get(today) or calc.daily_figures(business, today, today)[today]
    receivables = calc.receivables_snapshot(business, today)
    receivables_at_start = calc.receivables_outstanding_on(
        business, period.start - timedelta(days=1)
    )
    inventory = calc.inventory_snapshot(business)
    top = calc.top_products(business, period.start, period.end)
    categories = calc.sales_by_category(business, period.start, period.end)

    insights = InsightEngine().generate(
        InsightContext(
            currency=currency,
            period=period,
            current=current,
            previous=previous,
            changes=changes,
            receivables=receivables,
            receivables_at_start=receivables_at_start,
            inventory=inventory,
            top_products=top,
        )
    )

    def money(value):
        return quantize_money(value, currency)

    return {
        "generated_at": timezone.now(),
        "currency": currency,
        "period": _period_dict(period),
        "today": {
            "date": today.isoformat(),
            "sales_total": money(today_figures.revenue),
            "sales_count": today_figures.sales_count,
            "total_spending": money(today_figures.total_spending),
        },
        "figures": _figures_dict(current, currency),
        "previous": _figures_dict(previous, currency),
        "changes": changes,
        "daily": _daily_list(days, currency),
        "top_products": [
            {**item, "revenue": money(item["revenue"]), "profit": money(item["profit"])}
            for item in top
        ],
        "sales_by_category": [
            {"category": item["category"], "revenue": money(item["revenue"])} for item in categories
        ],
        "receivables": {
            "outstanding": money(receivables["outstanding"]),
            "overdue_amount": money(receivables["overdue_amount"]),
            "overdue_customers": receivables["overdue_customers"],
        },
        "inventory": inventory,
        "insights": [insight.as_dict() for insight in insights[:8]],
    }
