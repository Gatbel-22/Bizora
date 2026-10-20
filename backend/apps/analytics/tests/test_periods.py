from datetime import date, timedelta

from django.test import SimpleTestCase

from apps.analytics.periods import day_bounds, resolve_period


class ResolvePeriodTests(SimpleTestCase):
    today = date(2026, 10, 14)

    def resolve(self, name=None, **kwargs):
        return resolve_period(name, today=self.today, **kwargs)

    def test_today_compares_with_yesterday(self):
        period = self.resolve("today")
        self.assertEqual((period.start, period.end), (self.today, self.today))
        self.assertEqual(period.previous_start, date(2026, 10, 13))
        self.assertEqual(period.previous_end, date(2026, 10, 13))

    def test_last_7_days(self):
        period = self.resolve("last_7_days")
        self.assertEqual((period.start, period.end), (date(2026, 10, 8), date(2026, 10, 14)))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 10, 1), date(2026, 10, 7)),
        )
        self.assertEqual(period.days, 7)

    def test_last_30_days(self):
        period = self.resolve("last_30_days")
        self.assertEqual((period.start, period.end), (date(2026, 9, 15), date(2026, 10, 14)))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 8, 16), date(2026, 9, 14)),
        )

    def test_this_month_compares_with_the_same_days_last_month(self):
        period = self.resolve("this_month")
        self.assertEqual((period.start, period.end), (date(2026, 10, 1), date(2026, 10, 14)))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 9, 1), date(2026, 9, 14)),
        )

    def test_this_month_never_runs_past_the_end_of_a_shorter_month(self):
        period = resolve_period("this_month", today=date(2026, 3, 31))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 2, 1), date(2026, 2, 28)),
        )

    def test_last_month_compares_with_the_month_before(self):
        period = self.resolve("last_month")
        self.assertEqual((period.start, period.end), (date(2026, 9, 1), date(2026, 9, 30)))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 8, 1), date(2026, 8, 31)),
        )

    def test_last_month_across_a_new_year(self):
        period = resolve_period("last_month", today=date(2026, 1, 10))
        self.assertEqual((period.start, period.end), (date(2025, 12, 1), date(2025, 12, 31)))
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2025, 11, 1), date(2025, 11, 30)),
        )

    def test_custom_range_compares_with_the_equally_long_range_before(self):
        period = self.resolve(date_from=date(2026, 10, 1), date_to=date(2026, 10, 10))
        self.assertEqual(period.name, "custom")
        self.assertEqual(
            (period.previous_start, period.previous_end),
            (date(2026, 9, 21), date(2026, 9, 30)),
        )

    def test_unknown_period_names_are_refused(self):
        with self.assertRaises(ValueError):
            self.resolve("forever")

    def test_day_bounds_cover_whole_days(self):
        lower, upper = day_bounds(date(2026, 10, 1), date(2026, 10, 2))
        self.assertEqual(upper - lower, timedelta(days=2))
