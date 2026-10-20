# How Bizora works out profit

All figures are calculated on the server, from recorded sales and expenses. They are
**estimates**, not audited accounting figures.

| Figure               | Definition                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Revenue              | Total of completed sales, after discounts. Cancelled sales are excluded. Credit sales count when sold.                                                        |
| Cost of goods sold   | For each sold line: the product's cost at the time of sale x quantity.                                                                                        |
| Gross profit         | Revenue - cost of goods sold.                                                                                                                                 |
| Operating expenses   | Expenses in categories with "Count in profit" switched on.                                                                                                    |
| Estimated net profit | Gross profit - operating expenses.                                                                                                                            |
| Other spending       | Expenses in categories with "Count in profit" off (e.g. stock purchases). Not subtracted again, because the cost of stock is already counted when it is sold. |

## Distinctions

- Revenue is not cash: credit sales are revenue before any money arrives.
- Inventory value (stock at cost) is not cash.
- Customer receivables are not cash.

## Periods

Dates use the project time zone (Africa/Juba). "This month" is compared with the same
number of days at the start of last month; other periods with the equally long stretch
immediately before them. "Today" is not compared with a whole yesterday.

## Insights

Deterministic rules in `apps/analytics/insights.py`. Each rule is a function returning
zero or more insights with a severity (INFO, WARNING, CRITICAL).
