#!/usr/bin/env python3
"""FocusLine MCP Server — AI-powered focus music + Pomodoro timer.

Architecture: SIMPLE. No polling, no locks, no background state management.
- music() plays a track and writes state. Returns instantly.
- Pomodoro phase transitions use threading.Timer (one-shot callbacks).
- state.json is written only on events: play, stop, phase change.
- Statusline reads state.json every 2s (Claude Code refreshInterval).
"""

import atexit
import os
import random
import signal
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

for env_path in [Path.cwd() / ".env", Path.home() / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break


from mcp.server.fastmcp import FastMCP
from . import player, dj_agent, state
from .sources import local_cache, lyria, minimax_music, freesound, youtube, brainfm

mcp = FastMCP("productivity-music")

# ─── State: just simple variables, no locks needed (GIL protects single assignments) ───

_phase_timer: threading.Timer | None = None
_pomo_cycle: int = 0
_pomo_total: int = 0
_pomo_focus_min: int = 25
_pomo_break_min: int = 5
_user_context: str = ""


# ─── Cleanup ───

def _cleanup():
    global _phase_timer
    if _phase_timer:
        _phase_timer.cancel()
        _phase_timer = None
    player.stop()
    state.write({"playing": False})

atexit.register(_cleanup)

for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(_sig, lambda s, f: (_cleanup(), exit(0)))
    except (OSError, ValueError):
        pass


# ─── Helpers ───

def _find_cached_track() -> dict | None:
    """Find a cached mp3 track to play instantly."""
    tracks = local_cache.list_tracks()
    mp3s = [t for t in tracks if t["format"] == "mp3" and t["size_kb"] > 1000]
    if mp3s:
        pick = random.choice(mp3s)
        return {
            "path": pick["path"],
            "title": pick["name"].replace("_", " "),
            "source": "cache",
            "duration": pick["size_kb"] / 16,
        }
    return None


def _play_and_write(track: dict, pomo_fields: dict | None = None):
    """Play a track and write state. The ONLY function that writes state during playback."""
    player.play_loop(track["path"])

    data = {
        "playing": True,
        "track_name": track.get("title", Path(track["path"]).stem),
        "track_source": track.get("source", "unknown"),
        "track_start": time.time(),
        "track_duration": track.get("duration", 30),
    }
    if pomo_fields:
        data.update(pomo_fields)
    state.write(data)


def _get_pomo_fields(phase: str, cycle: int, phase_end: float) -> dict:
    """Build pomo fields dict."""
    return {
        "pomo_phase": phase,
        "pomo_cycle": cycle,
        "pomo_total": _pomo_total,
        "pomo_phase_end": phase_end,
        "pomo_focus_min": _pomo_focus_min,
        "pomo_break_min": _pomo_break_min,
    }


def _schedule_phase_change(seconds: float, callback):
    """Schedule a one-shot timer for phase transition."""
    global _phase_timer
    if _phase_timer:
        _phase_timer.cancel()
    _phase_timer = threading.Timer(seconds, callback)
    _phase_timer.daemon = True
    _phase_timer.start()


def _on_focus_end():
    """Called when a focus phase ends. Switches to break."""
    global _pomo_cycle
    if _pomo_cycle >= _pomo_total:
        _cleanup()
        return

    is_long = (_pomo_cycle >= _pomo_total)
    actual_break = _pomo_break_min * 3 if is_long else _pomo_break_min
    phase = "long_break" if is_long else "break"
    phase_end = time.time() + actual_break * 60

    # Find break music
    track = _find_cached_track()
    if not track:
        track = {"path": "", "title": "Break", "source": "none", "duration": actual_break * 60}

    if track["path"]:
        _play_and_write(track, _get_pomo_fields(phase, _pomo_cycle, phase_end))
    else:
        player.stop()
        state.write({"playing": False, **_get_pomo_fields(phase, _pomo_cycle, phase_end)})

    # Generate quote
    _update_quote(phase)

    _schedule_phase_change(actual_break * 60, _on_break_end)


def _on_break_end():
    """Called when a break ends. Starts next focus cycle."""
    global _pomo_cycle
    _pomo_cycle += 1

    if _pomo_cycle > _pomo_total:
        _cleanup()
        return

    phase_end = time.time() + _pomo_focus_min * 60

    # Find focus music — try DJ in background, use cache immediately
    track = _find_cached_track()
    if track:
        _play_and_write(track, _get_pomo_fields("focus", _pomo_cycle, phase_end))

    _update_quote("focus")

    # Try to find better music in background
    def _swap():
        try:
            result = dj_agent.recommend_and_play("Focus music, different style")
            if result.get("path"):
                _play_and_write(
                    {"path": result["path"], "title": result.get("title", ""),
                     "source": result.get("source", ""), "duration": 1800},
                    _get_pomo_fields("focus", _pomo_cycle, phase_end),
                )
        except Exception:
            pass
    threading.Thread(target=_swap, daemon=True).start()

    _schedule_phase_change(_pomo_focus_min * 60, _on_focus_end)


def _update_quote(phase: str = "focus"):
    """Generate a quote in background and write to state."""
    def _fetch():
        try:
            quote = dj_agent.generate_quote("", phase)
            if quote:
                s = state.read()
                s["quote"] = quote
                state.write(s)
        except Exception:
            pass
    threading.Thread(target=_fetch, daemon=True).start()


def _pick_timer_sync() -> dict:
    """Pick timer settings. Fast — just an API call."""
    try:
        return dj_agent._chat(
            'Pick Pomodoro preset. JSON only: {"focus":25,"break":5,"cycles":4,"reason":"why"}',
            f"Time: {dj_agent._get_context()['time_of_day']}",
            max_tokens=100, temperature=0.3,
        )
    except Exception:
        pass
    return {"focus": 25, "break": 5, "cycles": 4, "reason": "default"}


# ─── MCP Tools ───


@mcp.tool()
def set_context(context: str) -> str:
    """Tell the DJ what you're working on.

    Args:
        context: What you're doing and how you're feeling.
    """
    global _user_context
    _user_context = context
    return f"Context set: {context}"


@mcp.tool()
def music(request: str) -> str:
    """Start focus music with a Pomodoro timer.

    Plays music instantly from cache, finds better music in background.
    Pomodoro timer auto-picks settings based on time of day.
    Say 'stop' to end.

    IMPORTANT: Include context about what the user is doing and how they feel.

    Args:
        request: What the user wants + their context/mood.
    """
    global _pomo_cycle, _pomo_total, _pomo_focus_min, _pomo_break_min

    # Stop anything currently playing
    _cleanup()

    full_request = f"{request}. User context: {_user_context}" if _user_context else request

    # Play cached track instantly
    track = _find_cached_track()
    if track:
        _play_and_write(track)

    # Pick timer + find music in background, return instantly
    def _background():
        global _pomo_cycle, _pomo_total, _pomo_focus_min, _pomo_break_min

        # Pick timer
        import json as _json
        try:
            content = dj_agent._chat(
                'Pick Pomodoro preset. JSON only: {"focus":25,"break":5,"cycles":4,"reason":"why"}',
                f"Time: {dj_agent._get_context()['time_of_day']}",
                max_tokens=100, temperature=0.3,
            )
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            timer = _json.loads(content)
        except Exception:
            timer = {}

        _pomo_focus_min = timer.get("focus", 25)
        _pomo_break_min = timer.get("break", 5)
        _pomo_total = timer.get("cycles", 4)
        _pomo_cycle = 1

        # Find real music
        try:
            result = dj_agent.recommend_and_play(full_request)
            if result.get("path"):
                phase_end = time.time() + _pomo_focus_min * 60
                _play_and_write(
                    {"path": result["path"], "title": result.get("title", ""),
                     "source": result.get("source", ""), "duration": 1800},
                    _get_pomo_fields("focus", 1, phase_end),
                )
                _schedule_phase_change(_pomo_focus_min * 60, _on_focus_end)
                _update_quote("focus")
                return
        except Exception:
            pass

        # DJ failed — use cached track with timer
        phase_end = time.time() + _pomo_focus_min * 60
        s = state.read()
        s.update(_get_pomo_fields("focus", 1, phase_end))
        state.write(s)
        _schedule_phase_change(_pomo_focus_min * 60, _on_focus_end)
        _update_quote("focus")

    threading.Thread(target=_background, daemon=True).start()

    return "Music starting. Say 'stop' to end."


@mcp.tool()
def stop() -> str:
    """Stop music and Pomodoro timer."""
    _cleanup()
    return "Stopped."


@mcp.tool()
def now_playing() -> str:
    """Check what's playing."""
    s = state.read()
    if s.get("playing") and s.get("track_name"):
        name = s["track_name"]
        phase = s.get("pomo_phase", "")
        cycle = s.get("pomo_cycle", 0)
        total = s.get("pomo_total", 0)
        if phase:
            return f"Playing: {name} | {phase.upper()} {cycle}/{total}"
        return f"Playing: {name}"
    return "No music playing."


@mcp.tool()
def play_audio(file_path: str, loop: bool = False) -> str:
    """Play a specific audio file.

    Args:
        file_path: Path to the audio file.
        loop: Loop continuously.
    """
    if loop:
        player.play_loop(file_path)
    else:
        player.play(file_path, background=True)

    fp = Path(file_path)
    state.write({
        "playing": True,
        "track_name": fp.stem.replace("_", " "),
        "track_source": "local",
        "track_start": time.time(),
        "track_duration": 30,
    })
    return f"Playing: {fp.name}"


@mcp.tool()
def play_youtube(query: str) -> str:
    """Search and play from YouTube. Returns instantly, downloads in background.

    Args:
        query: Search query.
    """
    def _download():
        result = youtube.search_and_download(query)
        if result.get("path"):
            _play_and_write({
                "path": result["path"],
                "title": result.get("title", query),
                "source": "youtube",
                "duration": result.get("duration", 1800),
            })

    threading.Thread(target=_download, daemon=True).start()
    return "Searching YouTube..."


@mcp.tool()
def generate_lyria(mood: str = "focus") -> str:
    """Generate music with Google Lyria 3 AI. Returns instantly.

    Args:
        mood: focus, calm, energize, break, sleep.
    """
    def _generate():
        if mood in lyria.MOOD_PROMPTS:
            result = lyria.generate_for_mood(mood)
        else:
            result = lyria.generate(mood, "lyria_custom.mp3")
        if result.get("path"):
            _play_and_write({
                "path": result["path"],
                "title": result.get("title", mood),
                "source": "lyria3",
                "duration": 30,
            })

    threading.Thread(target=_generate, daemon=True).start()
    return "Generating with Lyria 3..."


@mcp.tool()
def list_tracks() -> str:
    """List cached audio tracks."""
    tracks = local_cache.list_tracks()
    if not tracks:
        return "No tracks cached."
    lines = [f"  {t['name']}.{t['format']} ({t['size_kb']} KB)" for t in tracks]
    return f"Tracks ({len(tracks)}):\n" + "\n".join(lines)


@mcp.tool()
def list_sources() -> str:
    """List available music sources."""
    return (
        "Sources:\n"
        "  brainfm: Curated 30-min focus tracks (default)\n"
        "  youtube: Search any music\n"
        f"  lyria3: {'Available' if os.environ.get('GOOGLE_API') else 'No GOOGLE_API key'}\n"
        f"  cache: {len(local_cache.list_tracks())} tracks cached"
    )
