from datetime import datetime


def parse_date(value: str) -> str:
    """Validate and normalize a YYYY-MM-DD date string."""
    try:
        return datetime.strptime(value, "%Y-%m-%d").strftime("%Y-%m-%d")
    except ValueError as exc:
        raise ValueError(f"Invalid date '{value}'. Expected YYYY-MM-DD.") from exc

