from decimal import Decimal


def _plain(value):
    return format(Decimal(value).normalize(), "f")


class InsufficientStockError(Exception):
    def __init__(self, product, available, requested):
        self.product = product
        self.available = available
        self.requested = requested
        super().__init__(
            f"Not enough stock: {product.name} has {_plain(available)} available "
            f"but {_plain(requested)} was requested."
        )


class NoStockChangeError(Exception):
    def __init__(self):
        super().__init__("The counted quantity is the same as the current stock.")
