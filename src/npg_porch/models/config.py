from datetime import datetime


def format_datetime(dt: datetime) -> str:
    """
    Convert datetime to YYYY-MM-DD HH:mm:ss format.
    """
    return dt.strftime("%Y-%m-%d\u00A0%H:%M:%S")


class DatetimeConfig:
    json_encoders = {datetime: format_datetime}
