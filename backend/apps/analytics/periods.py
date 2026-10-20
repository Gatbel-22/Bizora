from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from django.utils import timezone

PERIOD_NAMES = ("today", "last_7_days", "this_month", "last_30_days", "last_month")
DEFAULT_PERIOD = "this_month"
MAX_RANGE_DAYS = 366


@dataclass(frozen=True)
class Period:
    """A date range plus the range it should be compared with."""

    name: str
    start: date
    end: date
    previous_start: date
    previous_end: date

    @property
    def days(self):
        return (self.end - self.start).days + 1


def _first_of_previous_month(day):
    last_of_previous = day.replace(day=1) - timedelta(days=1)
    return last_of_previous.replace(day=1)


def resolve_period(name=None, date_from=None, date_to=None, today=None):
    """Turn a period name (or a custom date range) into dates, with its comparison range.

    Month periods compare like with like: "this month" so far is compared with the same
    number of days at the start of last month. Other periods compare with the
    equally long stretch immediately before them.
    """
    today = today or timezone.localdate()

    if date_from and date_to:
        label, start, end = "custom", date_from, date_to
    else:
        label = name or DEFAULT_PERIOD
        if label == "today":
            start = end = today
        elif label == "last_7_days":
            start, end = today - timedelta(days=6), today
        elif label == "last_30_days":
            start, end = today - timedelta(days=29), today
        elif label == "this_month":
            start, end = today.replace(day=1), today
        elif label == "last_month":
            end = today.replace(day=1) - timedelta(days=1)
            start = end.replace(day=1)
        else:
            raise ValueError(f"Unknown period: {label}")
    if label in ("this_month", "last_month"):
        previous_start = _first_of_previous_month(start)
        last_day_before = start - timedelta(days=1)
        if label == "this_month":
            # Month so far: compare with the same number of days, but never past the month's end.
            previous_end = min(previous_start + (end - start), last_day_before)
        else:
            # A finished month is compared with the whole month before it.
            previous_end = last_day_before
    else:
        length = (end - start).days + 1
        previous_end = start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=length - 1)

    return Period(label, start, end, previous_start, previous_end)


def day_bounds(start, end):
    """Start (inclusive) and end (exclusive) as timezone-aware datetimes covering whole days."""
    tz = timezone.get_current_timezone()
    lower = timezone.make_aware(datetime.combine(start, time.min), tz)
    upper = timezone.make_aware(datetime.combine(end + timedelta(days=1), time.min), tz)
    return lower, upper
