class OverpaymentError(Exception):
    def __init__(self, owed):
        self.owed = owed
        super().__init__(
            f"This customer only owes {owed:,.2f}. The payment can't be more than that."
        )


class NothingOwedError(Exception):
    def __init__(self, message="This customer has nothing outstanding to pay."):
        super().__init__(message)
