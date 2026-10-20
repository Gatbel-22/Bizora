from rest_framework import serializers

from .periods import MAX_RANGE_DAYS, PERIOD_NAMES


class PeriodQuerySerializer(serializers.Serializer):
    """Either a named period, or a custom date range (both dates)."""

    period = serializers.ChoiceField(choices=PERIOD_NAMES, required=False)
    date_from = serializers.DateField(required=False)
    date_to = serializers.DateField(required=False)

    def validate(self, attrs):
        has_dates = "date_from" in attrs or "date_to" in attrs
        if has_dates and "period" in attrs:
            raise serializers.ValidationError("Use either a period or a date range, not both.")
        if has_dates:
            if "date_from" not in attrs or "date_to" not in attrs:
                raise serializers.ValidationError(
                    {"date_to": "Both a start date and an end date are needed."}
                )
            if attrs["date_from"] > attrs["date_to"]:
                raise serializers.ValidationError(
                    {"date_to": "The end date can't be before the start date."}
                )
            if (attrs["date_to"] - attrs["date_from"]).days >= MAX_RANGE_DAYS:
                raise serializers.ValidationError(
                    {"date_to": f"Choose a range of at most {MAX_RANGE_DAYS} days."}
                )
        return attrs
