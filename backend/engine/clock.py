"""Injectable clock.

Services ask the clock for "now" instead of calling datetime.now() directly, so the demo
seeder can replay four weeks of simulated activity with realistic timestamps.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime


class Clock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class ManualClock(Clock):
    def __init__(self, start: datetime) -> None:
        if start.tzinfo is None:
            raise ValueError("ManualClock needs a timezone-aware datetime")
        self._now = start

    def now(self) -> datetime:
        return self._now

    def set(self, when: datetime) -> None:
        self._now = when


_current: Clock = Clock()


def now() -> datetime:
    return _current.now()


@contextmanager
def use_clock(clock: Clock) -> Iterator[Clock]:
    global _current
    previous = _current
    _current = clock
    try:
        yield clock
    finally:
        _current = previous
