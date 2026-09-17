"""Calendar handling -- DHRA_BUILD_SPEC.md section 4.5 and section 6
(Phase 3). "Never store a bare ISO date... when the calendar is unknown,
converted_iso is None and the item is excluded from temporal aggregates
with reason date_unresolved."

Real conversion math via `convertdate` (Julian day number algorithms),
not hand-rolled arithmetic -- calendar conversion is exactly the kind of
thing worth getting from a tested library rather than reproducing.
Gregorian, Julian and Islamic (tabular/civil, not observational --
see OPEN_QUESTIONS.md) are supported; Rumi (Ottoman fiscal) and regnal
calendars are not (they need period-specific lookup tables this project
doesn't have), and `convert_date_claim` returns those unconverted rather
than guessing.
"""

from __future__ import annotations

from datetime import date

from convertdate import gregorian, islamic, julian

from dhra.models import DateClaim

SUPPORTED_CALENDARS = frozenset({"gregorian", "julian", "hijri"})


def _to_gregorian_ymd(calendar: str, year: int, month: int, day: int) -> tuple[int, int, int]:
    if calendar == "gregorian":
        return year, month, day
    if calendar == "julian":
        return julian.to_gregorian(year, month, day)
    if calendar == "hijri":
        return islamic.to_gregorian(year, month, day)
    raise ValueError(f"unsupported calendar for conversion: {calendar!r}")


def _month_length(calendar: str, year: int, month: int) -> int:
    if calendar == "gregorian":
        return gregorian.month_length(year, month)
    if calendar == "julian":
        return julian.month_length(year, month)
    if calendar == "hijri":
        return islamic.month_length(year, month)
    raise ValueError(f"unsupported calendar: {calendar!r}")


def convert_date_claim(claim: DateClaim, *, year: int, month: int | None = None, day: int | None = None) -> DateClaim:
    """Returns a new DateClaim with `converted_iso` (day precision) or
    `range_start`/`range_end` (month/year precision) filled in, using the
    numeric (year, month, day) the caller parsed from
    `claim.original_expression` -- this module does not itself parse
    free-text dates (section 0 rule 4: no guessing). Calendars outside
    `SUPPORTED_CALENDARS` are returned unchanged (conversion_method stays
    None): not a defensible conversion, so none is offered.
    """
    if claim.calendar not in SUPPORTED_CALENDARS:
        return claim

    method = f"convertdate:{claim.calendar}->gregorian"

    if claim.precision == "day":
        if month is None or day is None:
            return claim
        gy, gm, gd = _to_gregorian_ymd(claim.calendar, year, month, day)
        return DateClaim(
            original_expression=claim.original_expression,
            calendar=claim.calendar,
            precision=claim.precision,
            asserted_by=claim.asserted_by,
            converted_iso=date(gy, gm, gd).isoformat(),
            conversion_method=method,
            range_start=claim.range_start,
            range_end=claim.range_end,
        )

    if claim.precision == "month":
        if month is None:
            return claim
        last_day = _month_length(claim.calendar, year, month)
        start_y, start_m, start_d = _to_gregorian_ymd(claim.calendar, year, month, 1)
        end_y, end_m, end_d = _to_gregorian_ymd(claim.calendar, year, month, last_day)
        return DateClaim(
            original_expression=claim.original_expression,
            calendar=claim.calendar,
            precision=claim.precision,
            asserted_by=claim.asserted_by,
            converted_iso=None,
            conversion_method=method,
            range_start=date(start_y, start_m, start_d).isoformat(),
            range_end=date(end_y, end_m, end_d).isoformat(),
        )

    if claim.precision == "year":
        start_y, start_m, start_d = _to_gregorian_ymd(claim.calendar, year, 1, 1)
        last_month = 12 if claim.calendar != "hijri" else 12
        last_day = _month_length(claim.calendar, year, last_month)
        end_y, end_m, end_d = _to_gregorian_ymd(claim.calendar, year, last_month, last_day)
        return DateClaim(
            original_expression=claim.original_expression,
            calendar=claim.calendar,
            precision=claim.precision,
            asserted_by=claim.asserted_by,
            converted_iso=None,
            conversion_method=method,
            range_start=date(start_y, start_m, start_d).isoformat(),
            range_end=date(end_y, end_m, end_d).isoformat(),
        )

    # decade / range / terminus_ante_quem / unknown precision: no
    # defensible single conversion without more structure than a bare
    # DateClaim carries -- left unconverted rather than guessed.
    return claim
