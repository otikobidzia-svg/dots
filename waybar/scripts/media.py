#!/usr/bin/env python3
"""MPRIS media capsule for waybar, driven by playerctl.

Hidden (class "empty") when nothing is playing.  Left-click toggles playback,
scroll steps through the queue.
"""

import json
import os
import subprocess

GLYPH = {"Playing": "\uf04b", "Paused": "\uf04c"}
COLOR = {"Playing": "#9ece6a", "Paused": "#e0af68"}
MAX_TEXT = 34


def playerctl(*args):
    try:
        result = subprocess.run(
            ("playerctl",) + args, capture_output=True, text=True, timeout=1.0
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip()


def clean(text):
    return " ".join(text.split())


def markup(text):
    return clean(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def clock(seconds):
    seconds = int(seconds)
    return f"{seconds // 60}:{seconds % 60:02d}"


def main():
    status = playerctl("status")
    if status not in GLYPH:
        print(json.dumps({"text": "", "tooltip": "", "class": "empty"}))
        return

    meta = playerctl(
        "metadata", "--format", "{{title}}\x1f{{artist}}\x1f{{album}}\x1f{{playerName}}\x1f{{mpris:length}}"
    )
    fields = (meta.split("\x1f") + [""] * 5)[:5]
    title, artist, album, player, length_us = fields

    if not title:
        location = playerctl("metadata", "--format", "{{xesam:url}}")
        title = os.path.basename(location) if location else "Unknown"
    title = clean(title)

    if not album:
        album = playerctl("metadata", "--format", "{{xesam:album}}")
    artist = clean(artist)
    album = clean(album)
    player = clean(player)

    line = f"{GLYPH[status]} {title}"
    if artist:
        line += f" \u2014 {artist}"
    if len(line) > MAX_TEXT:
        line = line[: MAX_TEXT - 1].rstrip() + "\u2026"

    try:
        position = float(playerctl("position") or 0)
        length = int(length_us) / 1_000_000 if length_us.isdigit() else 0
    except ValueError:
        position, length = 0.0, 0.0

    flags = []
    if playerctl("shuffle") == "On":
        flags.append("shuffle")
    if playerctl("repeat") == "On":
        flags.append("repeat")

    details = [f"<b>{markup(title)}</b>"]
    if artist or album:
        details.append(markup(" \u2014 ".join(part for part in (artist, album) if part)))
    if player:
        details.append(f"<tt>{markup(player)}"
                       + (f" \u00b7 {' \u00b7 '.join(flags)}" if flags else "")
                       + "</tt>")
    if length:
        details.append(f"<tt>{clock(position)} / {clock(length)}</tt>")
    details.append("<tt><small>click: play/pause \u00b7 scroll: prev/next</small></tt>")

    print(json.dumps({
        "text": f"<span foreground='{COLOR[status]}'>{GLYPH[status]}</span>"
                f" <span foreground='#c0caf5'>{markup(line[len(GLYPH[status]) + 1:])}</span>",
        "tooltip": "\n".join(details),
        "class": "playing" if status == "Playing" else "paused",
    }))


if __name__ == "__main__":
    main()
