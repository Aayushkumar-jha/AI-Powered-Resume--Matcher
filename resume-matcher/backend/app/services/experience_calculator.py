"""Professional experience calculation.

Finds employment date ranges (e.g. "Jan 2019 - Mar 2022", "06/2017 – Present", "2015 to 2018"),
converts them to month intervals, MERGES OVERLAPPING PERIODS (so two concurrent jobs are not
double-counted) and returns total years of experience plus a structured employment history.
"""
import re
from dataclasses import dataclass, field
from datetime import date

MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "sept": 9, "oct": 10, "nov": 11, "dec": 12,
}
_MONTH_RE = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"
_DATE_RE = (
    rf"(?:{_MONTH_RE}\s*[,']?\s*\d{{4}}"  # Jan 2019 / January, 2019
    r"|\d{1,2}\s*[/\-.]\s*\d{4}"           # 01/2019, 1-2019
    r"|\d{4}\s*[/\-.]\s*\d{1,2}(?!\d)"     # 2019-01
    r"|(?<!\d)\d{4}(?!\d))"                # 2019
)
_PRESENT_RE = r"(?:present|current(?:ly)?|now|today|till\s+date|to\s+date|ongoing|date)"
RANGE_RE = re.compile(
    rf"(?P<start>{_DATE_RE})\s*(?:-|–|—|to|until|till|through)\s*(?P<end>{_DATE_RE}|{_PRESENT_RE})",
    re.IGNORECASE,
)
STATED_YEARS_RE = re.compile(
    r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years|yrs)\s+(?:of\s+)?(?:professional\s+|industry\s+|hands[- ]on\s+|work\s+)?experience",
    re.IGNORECASE,
)


@dataclass
class EmploymentPeriod:
    start: tuple[int, int]  # (year, month)
    end: tuple[int, int]
    is_current: bool
    raw: str
    title: str | None = None
    company: str | None = None

    @property
    def start_idx(self) -> int:
        return self.start[0] * 12 + self.start[1] - 1

    @property
    def end_idx(self) -> int:  # exclusive
        return self.end[0] * 12 + self.end[1] - 1 + 1

    @property
    def months(self) -> int:
        return max(0, self.end_idx - self.start_idx)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "company": self.company,
            "start": f"{self.start[0]:04d}-{self.start[1]:02d}",
            "end": "Present" if self.is_current else f"{self.end[0]:04d}-{self.end[1]:02d}",
            "duration_months": self.months,
            "raw": self.raw,
        }


@dataclass
class ExperienceResult:
    total_years: float | None
    gross_years: float | None = None
    overlap_years: float = 0.0
    periods: list[EmploymentPeriod] = field(default_factory=list)
    method: str = "date_ranges"  # date_ranges | stated | not_found
    note: str = ""


def _parse_date(token: str, is_end: bool, today: date) -> tuple[tuple[int, int], bool, bool] | None:
    """Return ((year, month), is_current, month_known)."""
    t = token.strip().lower()
    if re.fullmatch(_PRESENT_RE, t, re.IGNORECASE):
        return (today.year, today.month), True, True
    m = re.match(rf"({_MONTH_RE})\s*[,']?\s*(\d{{4}})", t)
    if m:
        return (int(m.group(2)), MONTHS[m.group(1)[:3]]), False, True
    m = re.match(r"(\d{1,2})\s*[/\-.]\s*(\d{4})", t)
    if m and 1 <= int(m.group(1)) <= 12:
        return (int(m.group(2)), int(m.group(1))), False, True
    m = re.match(r"(\d{4})\s*[/\-.]\s*(\d{1,2})", t)
    if m and 1 <= int(m.group(2)) <= 12:
        return (int(m.group(1)), int(m.group(2))), False, True
    m = re.match(r"(\d{4})", t)
    if m:
        # Year only: start -> January; end -> treated as start of that year (exclusive),
        # so "2018 - 2020" counts as 24 months.
        return (int(m.group(1)), 1), False, False
    return None


def _guess_title_company(line: str, prev_line: str | None, match_text: str) -> tuple[str | None, str | None]:
    rest = line.replace(match_text, " ")
    rest = re.sub(r"[()\[\]]", " ", rest)
    rest = re.sub(r"\s{2,}", " ", rest).strip(" |,-–:\t")
    if len(rest) < 3 and prev_line:
        rest = prev_line.strip(" |,-–:\t•")
    if not rest:
        return None, None
    parts = [p.strip() for p in re.split(r"\s+\|\s+|\s+at\s+|\s+-\s+|\s+–\s+|,\s+|@", rest) if p.strip()]
    if not parts:
        return None, None
    title = parts[0][:120]
    company = parts[1][:120] if len(parts) > 1 else None
    return title, company


def merge_intervals(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping/adjacent [start, end) month intervals."""
    merged: list[list[int]] = []
    for s, e in sorted(intervals):
        if merged and s <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def calculate_experience(text: str, today: date | None = None, fallback_text: str | None = None) -> ExperienceResult:
    """Compute non-overlapping experience from `text` (ideally the Experience section)."""
    today = today or date.today()
    lines = text.split("\n")
    periods: list[EmploymentPeriod] = []
    prev_nonempty: str | None = None

    for line in lines:
        for m in RANGE_RE.finditer(line):
            start = _parse_date(m.group("start"), False, today)
            end = _parse_date(m.group("end"), True, today)
            if not start or not end:
                continue
            (sy, sm), _, _ = start
            (ey, em), is_current, end_month_known = end
            if not (1970 <= sy <= today.year) or ey > today.year + 1:
                continue
            if (ey, em) > (today.year, today.month):
                ey, em = today.year, today.month
            period = EmploymentPeriod(start=(sy, sm), end=(ey, em), is_current=is_current, raw=m.group(0))
            if not end_month_known and not is_current:
                # year-only end is exclusive: shift back one month, keep at least 1 year span
                end_idx = ey * 12  # exclusive Jan of end year
                if end_idx <= period.start_idx:
                    end_idx = period.start_idx + 12
                period.end = ((end_idx - 1) // 12, (end_idx - 1) % 12 + 1)
            if period.months <= 0:
                continue
            period.title, period.company = _guess_title_company(line, prev_nonempty, m.group(0))
            periods.append(period)
        if line.strip():
            prev_nonempty = line

    if periods:
        merged = merge_intervals([(p.start_idx, p.end_idx) for p in periods])
        total_m = sum(e - s for s, e in merged)
        gross_m = sum(p.months for p in periods)
        overlap = max(0, gross_m - total_m)
        note = f"Calculated from {len(periods)} employment period(s)"
        if overlap:
            note += f"; {round(overlap / 12, 1)} overlapping year(s) counted only once"
        return ExperienceResult(
            total_years=round(total_m / 12, 1), gross_years=round(gross_m / 12, 1),
            overlap_years=round(overlap / 12, 1), periods=periods, method="date_ranges", note=note,
        )

    # Fallback: explicitly stated experience ("5+ years of experience")
    m = STATED_YEARS_RE.search(fallback_text or text)
    if m:
        years = float(m.group(1))
        return ExperienceResult(total_years=years, method="stated",
                                note=f"No dated employment found; using stated '{m.group(0)}'")
    return ExperienceResult(total_years=None, method="not_found",
                            note="No employment dates or stated experience found in resume")
