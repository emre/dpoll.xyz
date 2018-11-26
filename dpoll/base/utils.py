import pytz
from datetime import datetime, date, time


def add_tz_info(t, timezone='UTC'):
    if t and isinstance(t, (datetime, date, time)) and t.tzinfo is None:
        utc = pytz.timezone(timezone)
        t = utc.localize(t)
    return t
