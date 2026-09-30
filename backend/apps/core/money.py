from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

# Every money column in Bizora uses these so amounts are exact (never floats).
MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2


@dataclass(frozen=True)
class Currency:
    code: str
    name: str
    symbol: str
    decimal_places: int = 2


_SUPPORTED = [
    Currency("SSP", "South Sudanese Pound", "SSP"),
    Currency("USD", "US Dollar", "$"),
    Currency("EUR", "Euro", "€"),
    Currency("KES", "Kenyan Shilling", "KSh"),
    Currency("UGX", "Ugandan Shilling", "USh", 0),
]

CURRENCIES = {c.code: c for c in _SUPPORTED}
CURRENCY_CHOICES = [(c.code, f"{c.code} - {c.name}") for c in _SUPPORTED]
DEFAULT_CURRENCY = "SSP"


def quantize_money(amount, currency_code=DEFAULT_CURRENCY):
    """Round an amount to the currency's decimal places."""
    places = CURRENCIES[currency_code].decimal_places
    return Decimal(amount).quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP)
