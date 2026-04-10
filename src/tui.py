#!/usr/bin/env python3
"""Productivity Music TUI — live progress bar, Pomodoro timer, playback controls.

Run in a tmux pane or separate terminal:
    python -m src.tui
    python -m src.tui --pomodoro
    python -m src.tui --pomodoro --focus 50 --break 10
    python -m src.tui --mode focus
    python -m src.tui --mode sleep
"""

import argparse
import os
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env
for p in [Path.cwd() / ".env", Path.cwd().parent / ".env", Path.home() / ".env"]:
    if p.exists():
        load_dotenv(p)
        break

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text
from rich.panel import Panel
from rich.layout import Layout
from rich import box

from . import player, dj_agent, state as shared_state
from .sources import procedural, lyria

console = Console()

# ─── State ───

class State:
    # Playback
    track_name: str = ""
    track_source: str = ""
    track_duration: float = 30.0
    track_start: float = 0.0
    playing: bool = False
    dj_reason: str = ""

    # Pomodoro
    pomo_active: bool = False
    pomo_cycle: int = 0
    pomo_total_cycles: int = 4
    pomo_phase: str = ""  # "focus" or "break" or "long_break"
    pomo_phase_end: float = 0.0
    pomo_focus_min: int = 25
    pomo_break_min: int = 5

    # General
    status_msg: str = "Ready"
    generating: bool = False

state = State()


# ─── Render ───

PHASE_COLORS = {
    "focus": "bold green",
    "break": "bold cyan",
    "long_break": "bold blue",
}

PHASE_LABELS = {
    "focus": "FOCUS",
    "break": "BREAK",
    "long_break": "LONG BREAK",
}


def make_bar(progress: float, width: int = 30) -> str:
    filled = int(progress * width)
    empty = width - filled
    return f"[green]{'█' * filled}[/green][dim]{'░' * empty}[/dim]"


def format_time(seconds: float) -> str:
    m, s = divmod(max(0, int(seconds)), 60)
    return f"{m}:{s:02d}"


def sync_from_mcp():
    """Check if MCP server updated state and sync to local TUI state."""
    s = shared_state.read()
    if not s or s.get("stale"):
        return
    # Only sync if TUI isn't driving its own playback
    if not state.pomo_active and not state.generating:
        if s.get("playing") and s.get("track_name"):
            state.playing = True
            state.track_name = s["track_name"]
            state.track_source = s.get("track_source", "MCP")
            state.track_start = s.get("track_start", time.time())
            state.track_duration = s.get("track_duration", 30.0)
            state.dj_reason = s.get("dj_reason", "")
        elif not s.get("playing"):
            state.playing = False
            state.track_name = ""


def render() -> Panel:
    now = time.time()
    sync_from_mcp()

    # Track info
    if state.playing and state.track_name:
        elapsed = min(now - state.track_start, state.track_duration)
        progress = elapsed / state.track_duration if state.track_duration > 0 else 0
        bar = make_bar(progress)
        track_line = f"[bold]▶[/bold] {state.track_name}  {bar}  {format_time(elapsed)}/{format_time(state.track_duration)}"
        source_line = f"[dim]Source: {state.track_source}[/dim]"
    elif state.generating:
        track_line = "[yellow]⟳ Generating...[/yellow]"
        source_line = f"[dim]{state.status_msg}[/dim]"
    else:
        track_line = "[dim]■ No audio playing[/dim]"
        source_line = ""

    # Pomodoro
    if state.pomo_active:
        remaining = max(0, state.pomo_phase_end - now)
        phase_color = PHASE_COLORS.get(state.pomo_phase, "white")
        phase_label = PHASE_LABELS.get(state.pomo_phase, state.pomo_phase)

        if state.pomo_phase == "focus":
            phase_total = state.pomo_focus_min * 60
        elif state.pomo_phase == "long_break":
            phase_total = state.pomo_break_min * 3 * 60
        else:
            phase_total = state.pomo_break_min * 60

        phase_elapsed = phase_total - remaining
        phase_progress = phase_elapsed / phase_total if phase_total > 0 else 0
        pomo_bar = make_bar(phase_progress, 20)

        pomo_line = (
            f"[{phase_color}]🍅 {phase_label}[/{phase_color}] "
            f"{state.pomo_cycle}/{state.pomo_total_cycles}  "
            f"{pomo_bar}  "
            f"[bold]{format_time(remaining)}[/bold] left"
        )
    else:
        pomo_line = "[dim]🍅 Pomodoro: inactive[/dim]"

    # Time of day
    hour = datetime.now().hour
    if 5 <= hour < 12:
        tod = "☀ Morning"
    elif 12 <= hour < 17:
        tod = "🌤 Afternoon"
    elif 17 <= hour < 21:
        tod = "🌅 Evening"
    else:
        tod = "🌙 Night"

    # DJ reason
    reason_line = f"[dim italic]{state.dj_reason[:80]}[/dim italic]" if state.dj_reason else ""

    # Assemble
    lines = [track_line]
    if source_line:
        lines.append(source_line)
    if reason_line:
        lines.append(reason_line)
    lines.append("")
    lines.append(pomo_line)
    lines.append("")
    lines.append(f"[dim]{tod} | {datetime.now().strftime('%H:%M:%S')} | Press Ctrl+C to quit[/dim]")

    content = "\n".join(lines)
    return Panel(content, title="[bold]Productivity Music[/bold]", box=box.ROUNDED, width=70)


# ─── Actions ───

def play_for_mood(mood: str):
    """Generate and play music for a mood."""
    state.generating = True
    state.status_msg = f"Asking DJ for {mood} music..."

    result = dj_agent.recommend_and_play(
        f"Play {mood} music. Session type: {mood}."
    )

    if "error" in result:
        state.status_msg = f"Error: {result['error']}"
        state.generating = False
        return

    path = result.get("path")
    if not path:
        state.status_msg = "No track produced"
        state.generating = False
        return

    # Estimate duration from file size (rough: mp3 ~128kbps = 16KB/s, wav ~176KB/s)
    file_path = Path(path)
    size = file_path.stat().st_size
    if file_path.suffix == ".wav":
        duration = size / (44100 * 2)  # mono 16-bit
    else:
        duration = size / (128 * 1000 / 8)  # ~128kbps mp3

    state.track_name = file_path.name
    state.track_source = result.get("source", "unknown")
    state.track_duration = duration
    state.track_start = time.time()
    state.dj_reason = result.get("dj_decision", {}).get("reason", "")
    state.generating = False
    state.playing = True

    # Write shared state so MCP/TUI stay in sync
    shared_state.write({
        "playing": True,
        "track_name": state.track_name,
        "track_source": state.track_source,
        "track_start": state.track_start,
        "track_duration": state.track_duration,
        "dj_reason": state.dj_reason,
    })

    player.play_loop(path)


def run_pomodoro(focus_min: int, break_min: int, cycles: int):
    """Run full Pomodoro in background thread."""
    state.pomo_active = True
    state.pomo_total_cycles = cycles
    state.pomo_focus_min = focus_min
    state.pomo_break_min = break_min

    for cycle in range(cycles):
        if not state.pomo_active:
            break

        # Focus phase
        state.pomo_cycle = cycle + 1
        state.pomo_phase = "focus"
        state.pomo_phase_end = time.time() + focus_min * 60
        state.status_msg = f"Focus session {cycle + 1}/{cycles}"

        play_for_mood("pomodoro_focus")

        # Wait for focus phase
        while time.time() < state.pomo_phase_end and state.pomo_active:
            # Check if track ended, restart if needed
            if not player.is_playing() and state.playing:
                path = Path(state.track_name)
                cached = Path.home() / ".productivity-music" / "cache" / state.track_name
                if cached.exists():
                    player.play_loop(str(cached))
            time.sleep(1)

        if not state.pomo_active:
            break

        # Break phase
        player.stop()
        state.playing = False

        is_last = (cycle + 1) == cycles
        if is_last:
            state.pomo_phase = "long_break"
            state.pomo_phase_end = time.time() + break_min * 3 * 60
            state.status_msg = f"Long break — rest well"
            play_for_mood("pomodoro_break")
        else:
            state.pomo_phase = "break"
            state.pomo_phase_end = time.time() + break_min * 60
            state.status_msg = f"Short break {cycle + 1}/{cycles}"
            play_for_mood("pomodoro_break")

        while time.time() < state.pomo_phase_end and state.pomo_active:
            time.sleep(1)

    state.pomo_active = False
    state.pomo_phase = ""
    player.stop()
    state.playing = False
    state.status_msg = "Pomodoro complete!"


# ─── Presets ───

PRESETS = {
    "1": {
        "name": "Classic Pomodoro",
        "desc": "25 min focus / 5 min break x 4 cycles",
        "note": "Recommended — backed by research, fits ultradian rhythm",
        "focus": 25, "break_min": 5, "cycles": 4,
        "recommended": True,
    },
    "2": {
        "name": "Deep Work",
        "desc": "50 min focus / 10 min break x 3 cycles",
        "note": "For flow-state programming sessions",
        "focus": 50, "break_min": 10, "cycles": 3,
    },
    "3": {
        "name": "Sprint",
        "desc": "15 min focus / 3 min break x 6 cycles",
        "note": "Short bursts — good for tasks you keep avoiding",
        "focus": 15, "break_min": 3, "cycles": 6,
    },
    "c": {
        "name": "Custom",
        "desc": "Set your own focus/break/cycles",
        "note": "You choose the timing",
    },
    "m": {
        "name": "Music Only",
        "desc": "Just play music, no timer",
        "note": "Pick a mood: focus, calm, sleep, energize, rain",
    },
}


def show_menu() -> tuple:
    """Show preset menu, return (mode, focus, break_min, cycles, music_mode)."""
    console.clear()
    console.print()
    console.print("[bold]  Productivity Music[/bold]")
    console.print("[dim]  Neuroscience-backed focus music + Pomodoro timer[/dim]")
    console.print()

    for key, preset in PRESETS.items():
        if preset.get("recommended"):
            badge = " [black on green] RECOMMENDED [/black on green]"
        else:
            badge = ""
        console.print(f"  [bold cyan]{key}[/bold cyan]  {preset['name']}{badge}")
        console.print(f"     [dim]{preset['desc']}[/dim]")
        console.print(f"     [italic dim]{preset['note']}[/italic dim]")
        console.print()

    console.print("[dim]  q  Quit[/dim]")
    console.print()

    choice = console.input("  [bold]Select [1/2/3/c/m/q]: [/bold]").strip().lower()

    if choice == "q":
        sys.exit(0)

    if choice in ("1", "2", "3"):
        p = PRESETS[choice]
        return ("pomodoro", p["focus"], p["break_min"], p["cycles"], None)

    if choice == "c":
        console.print()
        try:
            focus = int(console.input("  [bold]Focus minutes [25]: [/bold]").strip() or "25")
            brk = int(console.input("  [bold]Break minutes [5]: [/bold]").strip() or "5")
            cycles = int(console.input("  [bold]Cycles [4]: [/bold]").strip() or "4")
        except ValueError:
            focus, brk, cycles = 25, 5, 4
        return ("pomodoro", focus, brk, cycles, None)

    if choice == "m":
        console.print()
        console.print("  [dim]Modes: focus, calm, sleep, energize, rain, noise[/dim]")
        mode = console.input("  [bold]Mode [focus]: [/bold]").strip().lower() or "focus"
        return ("music", 0, 0, 0, mode)

    # Default to recommended
    p = PRESETS["1"]
    return ("pomodoro", p["focus"], p["break_min"], p["cycles"], None)


# ─── Main ───

def main():
    parser = argparse.ArgumentParser(description="Productivity Music TUI")
    parser.add_argument("--pomodoro", action="store_true", help="Start Pomodoro directly")
    parser.add_argument("--focus", type=int, default=25, help="Focus minutes")
    parser.add_argument("--break-min", type=int, default=5, help="Break minutes")
    parser.add_argument("--cycles", type=int, default=4, help="Cycles")
    parser.add_argument("--mode", type=str, default=None, help="Music mode (skip menu)")
    parser.add_argument("--preset", type=str, default=None,
                        choices=["1", "2", "3"], help="Preset number (skip menu)")
    args = parser.parse_args()

    # Skip menu if args provided
    if args.preset:
        p = PRESETS[args.preset]
        run_mode = "pomodoro"
        focus, brk, cycles, music_mode = p["focus"], p["break_min"], p["cycles"], None
    elif args.pomodoro:
        run_mode = "pomodoro"
        focus, brk, cycles, music_mode = args.focus, args.break_min, args.cycles, None
    elif args.mode:
        run_mode = "music"
        focus, brk, cycles, music_mode = 0, 0, 0, args.mode
    else:
        # Interactive menu
        run_mode, focus, brk, cycles, music_mode = show_menu()

    console.clear()

    if run_mode == "pomodoro":
        total = cycles * focus + (cycles - 1) * brk + brk * 3
        console.print(f"[bold]Pomodoro[/bold] — {focus}min focus / {brk}min break x {cycles} cycles (~{total}min)")
    else:
        console.print(f"[bold]Music[/bold] — {music_mode}")
    console.print()

    # Start background work
    if run_mode == "pomodoro":
        t = threading.Thread(
            target=run_pomodoro,
            args=(focus, brk, cycles),
            daemon=True,
        )
        t.start()
    else:
        t = threading.Thread(target=play_for_mood, args=(music_mode,), daemon=True)
        t.start()

    # Live render loop
    try:
        with Live(render(), console=console, refresh_per_second=2, screen=False) as live:
            while True:
                live.update(render())
                time.sleep(0.5)
    except KeyboardInterrupt:
        player.stop()
        state.pomo_active = False
        console.print("\n[dim]Stopped.[/dim]")


if __name__ == "__main__":
    main()
