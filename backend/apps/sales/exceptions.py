class SaleError(Exception):
    """A business rule was broken. `field` says which input the message belongs to."""

    def __init__(self, message, field="non_field_errors"):
        self.field = field
        super().__init__(message)
