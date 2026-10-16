# (name, counts toward profit?)
# "Inventory" is off: stock purchases become cost of goods sold when the goods are
# sold, so subtracting them again as an expense would count them twice.
DEFAULT_CATEGORIES = [
    ("Rent", True),
    ("Salaries", True),
    ("Utilities", True),
    ("Transport", True),
    ("Inventory", False),
    ("Marketing", True),
    ("Maintenance", True),
    ("Communication", True),
    ("Taxes & fees", True),
    ("Other", True),
]
