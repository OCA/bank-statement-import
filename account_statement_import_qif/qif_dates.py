# Copyright 2026 Ryan Duguid <ryan@duguid.com.au>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import re

# Numeric dates in these countries are written day-first (dd/mm/yyyy).
# Used only when the QIF file itself does not prove a format.
QIF_DAYFIRST_COUNTRIES = frozenset(
    {
        "AU",
        "NZ",
        "GB",
        "IE",
        "ZA",
        "IN",
        "DE",
        "FR",
        "ES",
        "IT",
        "NL",
        "BE",
        "PT",
        "AT",
        "CH",
        "SE",
        "NO",
        "DK",
        "FI",
        "PL",
        "BR",
    }
)

_QIF_DATE_SPLIT = re.compile(r"[/\-.]")


def qif_numeric_date_parts(raw):
    """Return integer date parts from a QIF date field, or an empty tuple."""
    parts = []
    for token in _QIF_DATE_SPLIT.split((raw or "").strip()):
        digits = "".join(char for char in token if char.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts)


def qif_file_dayfirst(date_strings):
    """Return True/False when the file proves dd/mm or mm/dd, else None.

    A first component above 12 is a day (31/07/2026). A second component
    above 12 is a month-first date (8/15/13). Year-first ISO dates are
    ignored. dateutil still parses each line independently, so a mixed
    file of 31/07/2026 and 08/07/2026 is otherwise imported as 31 July
    and 7 August.
    """
    saw_day_first = False
    saw_month_first = False
    for raw in date_strings:
        parts = qif_numeric_date_parts(raw)
        if len(parts) < 2:
            continue
        first, second = parts[0], parts[1]
        if first > 31:
            # 2026-07-31 — year first, not a day/month order signal
            continue
        if first > 12:
            saw_day_first = True
        elif 12 < second <= 31:
            saw_month_first = True
    if saw_day_first and not saw_month_first:
        return True
    if saw_month_first and not saw_day_first:
        return False
    return None
