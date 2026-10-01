#!/usr/bin/env python3
"""Clock capsule for waybar.

The stock waybar clock cannot be used on this build: its vendored fmt rejects
every format string except a bare "{}", so "{:%H:%M}" throws "invalid arg-id".
This script owns the layout instead - 24 h clock, weekday, full tooltip with
the month grid, week number and uptime.
"""

import calendar
import datetime
import json

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
MONTHS = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month_grid(now):
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdayscalendar(now.year, now.month)
    head = "  " + "".join(day[0] + " " for day in WEEKDAYS)
    rows = [head]
    for week in weeks:
        cells = "".join(
            f"{day:2} " if day else "   " for day in week
        )
        rows.append(cells)
    return "\n".join(rows)


def uptime():
    try:
        with open("/proc/uptime") as handle:
            seconds = int(float(handle.read().split()[0]))
    except (OSError, IndexError, ValueError):
        return "?"
    days, rest = divmod(seconds, 86400)
    hours, rest = divmod(rest, 3600)
    minutes = rest // 60
    parts = []
    if days:
        parts.append(f"{days} d")
    if days or hours:
        parts.append(f"{hours} h")
    parts.append(f"{minutes} m")
    return " ".join(parts)


def main():
    now = datetime.datetime.now()
    hour = now.hour
    suffix = f" {WEEKDAYS[now.weekday()]}"

    tooltip = (
        f"<big>{WEEKDAYS[now.weekday()]} {now.day} {MONTHS[now.month]} {now.year}</big>\n"
        f"<tt>week {now.isocalendar()[1]}  \u00b7  up {uptime()}</tt>\n"
        f"<tt>{month_grid(now)}</tt>"
    )

    print(json.dumps({
        "text": f"<span foreground='#c0caf5'>{hour:02d}:{now.minute:02d}</span>"
                f"<span foreground='#565f89'>{suffix}</span>",
        "tooltip": tooltip,
        "class": "weekend" if now.weekday() >= 5 else "weekday",
    }))


if __name__ == "__main__":
    main()
