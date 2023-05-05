import datetime
import pytz


def date_range(date_from: datetime.datetime, num_days: int, reverse: bool = False) -> list[datetime.datetime]:
    if reverse:
        return [date_from + datetime.timedelta(days=num_days-x-1) for x in range(num_days)]
    else:
        return [date_from + datetime.timedelta(days=x) for x in range(num_days)]


def strip_time(dt: datetime.datetime) -> datetime.datetime:
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def local_now_tz_aware():
    """Returns global current date/time in local representation with time zone"""
    return datetime.datetime.now(pytz.utc).astimezone()


def local_midnight_tz_aware() -> datetime.datetime:
    """Returns date/time of midnight in current location with time zone"""
    now = local_now_tz_aware()
    return strip_time(now)


def month_first_day(date: datetime.datetime = None):
    if date is None:
        date = local_midnight_tz_aware()
    return datetime.datetime(year=date.year, month=date.month, day=1)


def next_month_first_day(date: datetime.datetime = None):
    first_day = month_first_day(date)
    return month_first_day(first_day + datetime.timedelta(days=31))


def prev_month_first_day(date: datetime.datetime = None):
    first_day = month_first_day(date)
    return month_first_day(first_day - datetime.timedelta(days=1))


def month_last_day(date: datetime.datetime = None):
    return next_month_first_day(date) - datetime.timedelta(days=1)


def prev_month_last_day(date: datetime.datetime):
    return month_first_day(date) - datetime.timedelta(days=1)


def next_month_last_day(date: datetime.datetime):
    return month_last_day(next_month_first_day(date))
