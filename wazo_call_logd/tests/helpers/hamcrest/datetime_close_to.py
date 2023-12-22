from __future__ import annotations

from datetime import datetime, timedelta, tzinfo
from typing import Any

import dateutil
from hamcrest.core.base_matcher import BaseMatcher, Description


def is_valid_date_string(s: str, format=None) -> bool:
    try:
        if format:
            datetime.strptime(s, format)
        else:
            datetime.fromisoformat(s)
        return True
    except (ValueError, TypeError):
        return False


class DatetimeRelativeMatcher(BaseMatcher[datetime]):
    def __init__(self, reference: datetime, delta: timedelta) -> None:
        self.delta = delta
        self.reference = reference

    def _matches(self, item: Any) -> bool:
        if not isinstance(item, datetime):
            try:
                item = dateutil.parser.isoparse(str(item))
            except ValueError:
                return False

        return (
            bool(self.reference.tzinfo)
            if item.tzinfo
            else not bool(self.reference.tzinfo)
        ) and self._diff(item) <= self.delta

    def _diff(self, item: datetime) -> timedelta:
        return abs(item - self.reference)

    def describe_mismatch(self, item: Any, mismatch_description: Description) -> None:
        try:
            item = dateutil.parser.isoparse(item)
        except ValueError:
            super().describe_mismatch(item, mismatch_description)
            mismatch_description.append_text(
                ' where {repr(item)} is of type {type(item)}'
            )
        else:
            if item.tzinfo and not self.reference.tzinfo:
                mismatch_description.append_description_of(item).append_text(
                    ' is timezone aware but reference datetime is naive'
                )
            elif not item.tzinfo and self.reference.tzinfo:
                mismatch_description.append_description_of(item).append_text(
                    ' is time zone naive but reference datetime is time zone aware'
                )
            else:
                actual_delta = self._diff(item)
                mismatch_description.append_description_of(item).append_text(
                    ' differed by '
                ).append_description_of(actual_delta).append_text(
                    ' of '
                ).append_description_of(
                    self.reference
                )

    def describe_to(self, description: Description) -> None:
        description.append_text(' a datetime value within ').append_description_of(
            self.delta
        ).append_text(' of ').append_description_of(self.reference)


class DatetimeMatcher(BaseMatcher[datetime]):
    def __init__(
        self,
        year=None,
        month=None,
        day=None,
        hour=None,
        minute=None,
        second=None,
        microsecond=None,
        tz: tzinfo | None = None,
    ):
        self.year = year
        self.month = month
        self.day = day
        self.hour = hour
        self.minute = minute
        self.second = second
        self.microsecond = microsecond
        self.tz = tz

    def _matches(self, item: Any) -> bool:
        if not isinstance(item, datetime):
            return False
        return all(self._attributes_match(item).values())

    def _attributes_match(self, item: datetime) -> dict[str, bool]:
        return {
            'year': self.year is None or (item.year == self.year),
            'month': self.month is None or (item.month == self.month),
            'day': self.day is None or (item.day == self.day),
            'hour': self.hour is None or (item.hour == self.hour),
            'minute': self.minute is None or (item.minute == self.minute),
            'second': self.second is None or (item.second == self.second),
            'microsecond': self.microsecond is None
            or (item.microsecond == self.microsecond),
            'tz': self.tz is None or (item.tzinfo == self.tz),
        }

    def describe_mismatch(self, item: Any, mismatch_description: Description) -> None:
        if not isinstance(item, datetime):
            super().describe_mismatch(item, mismatch_description)
        else:
            attributes_mismatch = [
                name for name, value in self._attributes_match(item).items() if value
            ]
            mismatch_description.append_description_of(item).append_text(
                ' had attributes ({}) but attributes ({}) were expected'.format(
                    ', '.join(
                        f'{name}={getattr(item, name)}' for name in attributes_mismatch
                    ),
                    ', '.join(
                        f'{name}={getattr(self, name)}' for name in attributes_mismatch
                    ),
                )
            )

    def describe_to(self, description: Description) -> None:
        description.append_text(
            ' a datetime value with attributes ({}) '.format(
                ', '.join(
                    f"{name}={getattr(self, name)}"
                    for name in vars(self)
                    if getattr(self, name) is not None
                )
            )
        )


def datetime_close_to(
    reference: str | datetime, delta: timedelta = timedelta(seconds=1)
):
    if isinstance(reference, str):
        reference = dateutil.parser.isoparse(reference)
    return DatetimeRelativeMatcher(reference, delta)
