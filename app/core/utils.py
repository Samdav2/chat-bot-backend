from datetime import datetime, timezone


def utc_now() -> datetime:
    """Return timezone-naive UTC datetime compatible with PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
