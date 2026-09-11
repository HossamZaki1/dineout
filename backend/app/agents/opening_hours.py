"""Opening times calculated in the restaurant's timezone, never server time."""
import math
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def next_opening(periods, *, now=None, timezone_id=None, utc_offset_minutes=None,
                 next_open_time=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("The clock must be timezone-aware")
    zone = None
    if timezone_id:
        try:
            zone = ZoneInfo(timezone_id)
        except ZoneInfoNotFoundError:
            pass
    if zone is None and utc_offset_minutes is not None:
        zone = timezone(timedelta(minutes=utc_offset_minutes))
    if zone is None:
        return None, "Hours not available"
    local_now = now.astimezone(zone)
    candidates = []
    if next_open_time:
        try:
            supplied = datetime.fromisoformat(next_open_time.replace("Z", "+00:00"))
            if supplied.tzinfo is not None and supplied > now:
                # Google's nextOpenTime accounts for exceptional hours.
                return describe_opening(supplied.astimezone(zone), local_now)
        except (TypeError, ValueError):
            pass

    google_day = (local_now.weekday() + 1) % 7
    for period in periods or []:
        opening = period.get("open", {})
        if not opening or opening.get("truncated"):
            continue
        try:
            hour, minute = opening.get("hour", 0), opening.get("minute", 0)
            if opening.get("date"):
                date = opening["date"]
                candidate = datetime(date["year"], date["month"], date["day"],
                                     hour, minute, tzinfo=zone)
            else:
                days = (opening["day"] - google_day) % 7
                candidate = (local_now + timedelta(days=days)).replace(
                    hour=hour, minute=minute, second=0, microsecond=0)
                if candidate.astimezone(timezone.utc) <= now.astimezone(timezone.utc):
                    candidate += timedelta(days=7)
            if candidate.astimezone(timezone.utc) > now.astimezone(timezone.utc):
                candidates.append(candidate)
        except (KeyError, TypeError, ValueError):
            continue
    if not candidates:
        return None, "Hours not available"
    return describe_opening(min(candidates, key=lambda d: d.timestamp()), local_now)


def describe_opening(opening, now):
    minutes = (opening.timestamp() - now.timestamp()) / 60
    clock = opening.strftime("%I:%M %p").lstrip("0")
    if minutes < 60:
        label = f"Opens in {max(1, math.ceil(minutes))} min"
    elif opening.date() == now.date():
        label = f"Opens today at {clock}"
    elif opening.date() == (now + timedelta(days=1)).date():
        label = f"Opens tomorrow at {clock}"
    else:
        label = f"Opens {opening.strftime('%A')} at {clock}"
    return minutes, label
