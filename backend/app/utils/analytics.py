"""Pure helper functions for analytics (no database access -> easy to unit-test)."""
from datetime import date, datetime, timedelta, timezone

VALID_PERIODS = {'day', 'week', 'month', 'all'}

# Rolling windows: "last N days counting back from now".
PERIOD_DAYS = {'week': 7, 'month': 30}


def get_period_start(period: str, now: datetime | None = None) -> datetime | None:
    """
    Returns the UTC datetime from which sessions are counted for the given period.
    Returns None for 'all' (= no lower bound).

    - 'day'   -> today at 00:00 UTC
    - 'week'  -> last 7 days (rolling window)
    - 'month' -> last 30 days (rolling window)

    `now` can be passed in for deterministic tests.
    """
    if period not in VALID_PERIODS:
        raise ValueError(f'Unknown period: {period!r}')

    now = now or datetime.now(timezone.utc)

    if period == 'day':
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if period in PERIOD_DAYS:
        return now - timedelta(days=PERIOD_DAYS[period])
    return None  # 'all'


def calculate_percentage(part: int | float, total: int | float, ndigits: int = 1) -> float:
    """Returns part/total as a percentage. Returns 0.0 when total is 0 (no ZeroDivisionError)."""
    if total <= 0:
        return 0.0
    return round(part / total * 100, ndigits)


def calculate_streak(study_dates: list[date], today: date | None = None) -> int:
    """
    Counts consecutive days with study sessions.

    `study_dates` must contain UNIQUE dates sorted from newest to oldest.
    The streak is still alive if the last session was today or yesterday
    (so the user does not lose it before they had a chance to study today).
    """
    if not study_dates:
        return 0

    today = today or datetime.now(timezone.utc).date()  # same timezone as the stored dates
    yesterday = today - timedelta(days=1)

    if study_dates[0] < yesterday:
        return 0

    streak = 0
    expected_date = study_dates[0]
    for d in study_dates:
        if d != expected_date:
            break  # gap found -> streak is over
        streak += 1
        expected_date -= timedelta(days=1)

    return streak
