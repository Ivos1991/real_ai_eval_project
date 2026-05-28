"""Date normalization helpers used by deterministic extraction metrics."""

import re
from datetime import datetime

MONTHS = {
    "jan": "January",
    "feb": "February",
    "mar": "March",
    "apr": "April",
    "may": "May",
    "jun": "June",
    "jul": "July",
    "aug": "August",
    "sep": "September",
    "sept": "September",
    "oct": "October",
    "nov": "November",
    "dec": "December",
}

DATE_PATTERNS = [
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
]


def normalize_date(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _canonicalize_month_aliases(re.sub(r"\s+", " ", value.strip()))
    for pattern in DATE_PATTERNS:
        try:
            return datetime.strptime(cleaned, pattern).date().isoformat()
        except ValueError:
            continue
    return None


def _canonicalize_month_aliases(value: str) -> str:
    cleaned = value.replace(".", "")
    for alias, month in MONTHS.items():
        cleaned = re.sub(rf"\b{alias}\b", month, cleaned, flags=re.IGNORECASE)
    return cleaned


def candidate_dates(text: str) -> list[str]:
    patterns = [
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|Sept\.?|October|November|December|"
        r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{1,2},\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December|"
        r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sept\.?|Oct\.?|Nov\.?|Dec\.?)\s+\d{4}\b",
    ]
    matches: list[str] = []
    for pattern in patterns:
        matches.extend(match.group(0).replace(".", "") for match in re.finditer(pattern, text, flags=re.IGNORECASE))
    return matches
