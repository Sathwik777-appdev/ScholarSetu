"""Place names typed by people ("dumka ", "DUMKA") must still match officers' jurisdictions."""

from typing import Optional

from sqlalchemy import func


def tidy(name: Optional[str]) -> Optional[str]:
    """How a place name is stored: single spaces, title case ("west  singhbhum " -> "West Singhbhum")."""
    return " ".join(name.split()).title() if name else name


def key(name: Optional[str]) -> str:
    """How place names are compared: case and spacing ignored."""
    return " ".join((name or "").split()).casefold()


def sql_key(column):
    """The same comparison key, in SQL."""
    return func.lower(func.regexp_replace(func.trim(column), r"\s+", " ", "g"))
