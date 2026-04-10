#!/usr/bin/env python3
"""Productivity Music status line for Claude Code.

Outputs 1-2 lines showing music player and Pomodoro timer state.
Only outputs when music is playing or pomodoro is active.
Outputs nothing when idle — won't interfere with other status lines.

Install:
    Add to ~/.claude/settings.json:
    {
        "statusLine": {
            "type": "command",
            "command": "productivity-music-status",
            "refreshInterval": 2
        }
    }
"""
import json, sys, time
from pathlib import Path


def main():
    _run()


def _run():
    # Consume stdin (Claude Code sends context, we don't use it)
    try:
        sys.stdin.read()
    except Exception:
        pass

    # Read music state
    sf = Path.home() / ".productivity-music" / "state.json"
    try:
        s = json.loads(sf.read_text()) if sf.exists() else {}
    except Exception:
        s = {}

    now = time.time()
    updated = float(s.get("updated_at", 0))
    age = now - updated
    now = int(now)

    # Show status as long as playing=true, even if poller is slow.
    # Only hide after 30s stale (server genuinely stopped).
    stale = age > 30

    playing = s.get("playing") and s.get("track_name") and not stale
    phase = s.get("pomo_phase")
    pomo_active = phase and phase != "null" and not stale

    # Nothing to show — output nothing, don't take up space
    if not playing and not pomo_active:
        return

    lines = []

    # ─── Music Player ───
    if playing:
        start = int(float(s.get("track_start", now)))
        dur = int(float(s.get("track_duration", 30)))
        raw_elapsed = now - start
        total_played = raw_elapsed
        tm, ts = divmod(int(total_played), 60)

        source = s.get("track_source", "")
        source_tag = f" \033[90m[{source}]\033[0m" if source else ""

        lines.append(
            f"\033[32m▶\033[0m {s['track_name']}{source_tag}"
        )

    # ─── Pomodoro Timer ───
    if pomo_active:
        pend = int(float(s.get("pomo_phase_end", now)))
        rem = max(0, pend - now)
        pm, ps = divmod(rem, 60)
        cycle = s.get("pomo_cycle", 0)
        total = s.get("pomo_total", 0)

        colors = {"focus": "32", "break": "36", "long_break": "34"}
        labels = {"focus": "FOCUS", "break": "BREAK", "long_break": "LONG BREAK"}
        icons = {"focus": "🎯", "break": "☕", "long_break": "🌿"}
        c = colors.get(phase, "0")
        l = labels.get(phase, phase)
        icon = icons.get(phase, "🍅")

        focus_min = int(float(s.get("pomo_focus_min", 25)))
        break_min = int(float(s.get("pomo_break_min", 5)))
        if phase == "focus":
            phase_total = focus_min * 60
        elif phase == "long_break":
            phase_total = break_min * 3 * 60
        else:
            phase_total = break_min * 60

        phase_elapsed = max(0, phase_total - rem)
        phase_pct = phase_elapsed * 15 // phase_total if phase_total > 0 else 0
        pbar = "█" * phase_pct + "░" * (15 - phase_pct)

        dots = ""
        for i in range(1, total + 1):
            if i < cycle:
                dots += "\033[32m●\033[0m"
            elif i == cycle:
                dots += f"\033[{c}m●\033[0m"
            else:
                dots += "\033[90m○\033[0m"

        lines.append(
            f"{icon} \033[{c}m{l}\033[0m"
            f"  {pbar}"
            f"  \033[1m{pm}:{ps:02d}\033[0m"
            f"  {dots}"
        )

    # Motivational quote
    quote = s.get("quote", "")
    if quote:
        lines.append(f"\033[3;90m  \"{quote}\"\033[0m")

    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
