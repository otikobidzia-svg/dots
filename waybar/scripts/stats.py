#!/usr/bin/env python3
"""Compact system-stats capsule for waybar: CPU - RAM - Disk - Temp - Backlight.

Emits waybar's custom-module JSON.  The text is pango markup, so each icon
carries its own colour.  Click the pill to open btop.
"""

import glob
import json
import os
import shutil

RUNTIME = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
STATE = os.path.join(RUNTIME, "waybar-stats-state.json")

C_CPU, C_MEM, C_DISK, C_TEMP, C_BRI = "#7aa2f7", "#bb9af7", "#89ddff", "#e0af68", "#f7768e"
C_WARM, C_HOT = "#e0af68", "#f7768e"


def read(path, default=""):
    try:
        with open(path) as handle:
            return handle.read().strip()
    except OSError:
        return default


def human(num_bytes):
    size = float(num_bytes)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TiB"


def cpu_usage():
    """Instant CPU load from the /proc/stat deltas between two invocations."""
    fields = read("/proc/stat").split("\n")[0].split()
    if len(fields) < 5:
        return 0, 0
    ticks = [int(value) for value in fields[1:]]
    total, idle = sum(ticks), ticks[3] + (ticks[4] if len(ticks) > 4 else 0)

    previous = {}
    try:
        with open(STATE) as handle:
            previous = json.load(handle)
    except (OSError, ValueError):
        pass

    percent = previous.get("percent", 0)
    if "total" in previous and total > previous["total"]:
        elapsed = total - previous["total"]
        resting = idle - previous.get("idle", 0)
        percent = max(0, min(100, round(100 * (1 - resting / elapsed))))

    try:
        with open(STATE, "w") as handle:
            json.dump({"total": total, "idle": idle, "percent": percent}, handle)
    except OSError:
        pass

    try:
        threads = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        threads = os.cpu_count() or 1
    return percent, threads


def cpu_ghz():
    for line in read("/proc/cpuinfo").split("\n"):
        if line.startswith("cpu MHz"):
            try:
                return round(float(line.split(":")[1]) / 1000, 2)
            except (IndexError, ValueError):
                break
    return 0


def memory_usage():
    info = {}
    for line in read("/proc/meminfo").split("\n"):
        key, _, rest = line.partition(":")
        values = rest.split()
        if values and values[0].isdigit():
            info[key] = int(values[0]) * 1024
    total = info.get("MemTotal", 0)
    available = info.get("MemAvailable", info.get("MemFree", 0))
    return total - available, total


def disk_usage(path="/"):
    usage = shutil.disk_usage(path)
    return usage.used, usage.total


def cpu_temp():
    for name_file in sorted(glob.glob("/sys/class/hwmon/hwmon*/name")):
        if read(name_file) != "coretemp":
            continue
        value = read(os.path.join(os.path.dirname(name_file), "temp1_input"))
        if value.isdigit():
            return round(int(value) / 1000)
    return None


def backlight():
    for base in sorted(glob.glob("/sys/class/backlight/*")):
        raw = read(os.path.join(base, "actual_brightness")) or read(
            os.path.join(base, "brightness")
        )
        highest = read(os.path.join(base, "max_brightness"))
        if raw.isdigit() and highest.isdigit() and int(highest) > 0:
            return round(100 * int(raw) / int(highest))
    return None


def uptime():
    seconds = int(float(read("/proc/uptime", "0").split()[0] or 0))
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


def pill(icon, color, value):
    return f"<span foreground='{color}'>{icon}</span> <span foreground='#a9b1d6'>{value}</span>"


def main():
    cpu, threads = cpu_usage()
    mem_used, mem_total = memory_usage()
    disk_used, disk_total = disk_usage()
    temp = cpu_temp()
    bright = backlight()

    items = [
        ("\uf2db", C_CPU, f"{cpu}%"),
        ("\uf053", C_MEM, human(mem_used)),
        ("\uf0a0", C_DISK, f"{round(100 * disk_used / disk_total) if disk_total else 0}%"),
    ]
    if temp is not None:
        if temp >= 85:
            temp_color = C_HOT
        elif temp >= 75:
            temp_color = C_WARM
        else:
            temp_color = C_TEMP
        items.append(("\uf2c5", temp_color, f"{temp}\u00b0"))
    if bright is not None:
        items.append(("\uf185", C_BRI, f"{bright}%"))

    lines = [
        f"<b>CPU</b>\t{cpu}%  \u00b7  {threads} threads @ {cpu_ghz()} GHz",
        f"<b>RAM</b>\t{human(mem_used)} / {human(mem_total)}"
        f"  ({round(100 * mem_used / mem_total) if mem_total else 0}%)",
        f"<b>Disk</b>\t{human(disk_used)} / {human(disk_total)}"
        f"  ({round(100 * disk_used / disk_total) if disk_total else 0}%)",
    ]
    if temp is not None:
        lines.append(f"<b>Temp</b>\t{temp} \u00b0C  (hwmon coretemp)")
    if bright is not None:
        lines.append(f"<b>Backlight</b>\t{bright}%")
    lines.append(f"<b>Uptime</b>\t{uptime()}")

    state = "normal"
    if temp is not None:
        state = "hot" if temp >= 85 else "warm" if temp >= 75 else "normal"

    print(json.dumps({
        "text": "  ".join(pill(*item) for item in items),
        "tooltip": "\n".join(lines),
        "class": state,
    }))


if __name__ == "__main__":
    main()
