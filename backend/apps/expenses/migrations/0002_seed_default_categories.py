from django.db import migrations

DEFAULTS = [
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


def add_default_categories(apps, schema_editor):
    Business = apps.get_model("businesses", "Business")
    Category = apps.get_model("expenses", "ExpenseCategory")
    for business in Business.objects.all():
        existing = {
            name.lower()
            for name in Category.objects.filter(business=business).values_list("name", flat=True)
        }
        Category.objects.bulk_create(
            [
                Category(business=business, name=name, affects_profit=affects_profit)
                for name, affects_profit in DEFAULTS
                if name.lower() not in existing
            ]
        )


class Migration(migrations.Migration):
    dependencies = [
        ("expenses", "0001_initial"),
        ("businesses", "0001_initial"),
    ]

    operations = [migrations.RunPython(add_default_categories, migrations.RunPython.noop)]