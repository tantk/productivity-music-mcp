#!/usr/bin/env python3
"""Productivity Music MCP Server — GLM 5.1 DJ-managed, multi-source audio plugin.

State architecture: EVENT-DRIVEN writes only.
- state.json is written ONLY when something changes (play, stop, phase change, track swap)
- No poller thread -- statusline reads state.json every 2s via refreshInterval
- _current_track is the single source of truth, protected by _track_lock
- Only _write_state() writes to disk, always from _current_track
"""

import atexit
import os
import queue
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
from .sources import local_cache, lyria, minimax_music, freesound, youtube

mcp = FastMCP("productivity-music")

# ─── Shared State ───

_track_lock = threading.Lock()
_current_track: dict = {}
_pomodoro_stop = threading.Event()
_pomodoro_stop.set()  # Start in stopped state
_pomodoro_thread: threading.Thread | None = None
_user_context: str = ""
_current_quote: str = ""
_last_quote_time: float = 0


def _write_state():
    """Write current state to disk. ONLY place that writes state.json."""
    with _track_lock:
        if _current_track and _current_track.get("track_name"):
            data = dict(_current_track)
            data["playing"] = True
            data["quote"] = _current_quote
        else:
            data = {"playing": False}
    state.write(data)


def _set_track(result: dict, preserve_pomo: bool = True):
    """Update _current_track from a DJ result and write state.

    Calls _make_track_info OUTSIDE the lock (it does ffprobe/GLM calls),
    then assigns under lock.
    """
    global _current_track
    if "path" not in result:
        return

    # Heavy work outside lock
    info = _make_track_info(result)

    with _track_lock:
        if preserve_pomo:
            for k in ("pomo_phase", "pomo_cycle", "pomo_total", "pomo_phase_end",
                       "pomo_focus_min", "pomo_break_min"):
                if k in _current_track:
                    info[k] = _current_track[k]
        _current_track = info

    _write_state()


def _set_pomo_fields(phase: str, cycle: int, total: int, phase_end: float,
                     focus_min: int, break_min: int):
    """Update pomodoro fields in _current_track and write state."""
    with _track_lock:
        _current_track["pomo_phase"] = phase
        _current_track["pomo_cycle"] = cycle
        _current_track["pomo_total"] = total
        _current_track["pomo_phase_end"] = phase_end
        _current_track["pomo_focus_min"] = focus_min
        _current_track["pomo_break_min"] = break_min
    _write_state()


def _clear_track():
    """Clear track and write stopped state."""
    global _current_track
    with _track_lock:
        _current_track = {}
    _write_state()


def _refresh_quote():
    """Generate a new motivational quote in background."""
    global _current_quote, _last_quote_time
    now = time.time()
    if now - _last_quote_time < 60:
        return

    with _track_lock:
        phase = _current_track.get("pomo_phase", "focus")
        track = _current_track.get("track_name", "")

    def _fetch():
        global _current_quote, _last_quote_time
        try:
            _current_quote = dj_agent.generate_quote(track, phase)
            _last_quote_time = time.time()
            _write_state()  # Write new quote to disk
        except Exception:
            pass

    threading.Thread(target=_fetch, daemon=True).start()


# ─── Cleanup ───

def _cleanup():
    player.stop()
    _clear_track()

atexit.register(_cleanup)

def _signal_handler(sig, frame):
    _cleanup()
    raise SystemExit(0)

for _sig in (signal.SIGTERM, signal.SIGINT):
    try:
        signal.signal(_sig, _signal_handler)
    except (OSError, ValueError):
        pass


# ─── Helpers ───

def _get_duration(file_path: str) -> float:
    """Get audio duration using ffprobe, fallback to file size estimate."""
    import subprocess, json as _json
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", file_path],
            capture_output=True, text=True, timeout=10,
        )
        data = _json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        pass
    fp = Path(file_path)
    sz = fp.stat().st_size
    if fp.suffix == ".wav":
        return sz / (44100 * 2 * 2)  # stereo 16-bit
    return sz / (128 * 1000 / 8)


def _make_track_info(result: dict) -> dict:
    """Build track info dict. May be slow (ffprobe + GLM naming). Call OUTSIDE locks."""
    fp = Path(result["path"])
    title = result.get("title", "")

    if not title:
        source = result.get("source", "")
        if source in ("local_cache", "lyria3"):
            try:
                from .sources.lyria import _name_track
                desc = result.get("model_response", "") or fp.stem
                title = _name_track(desc)
            except Exception:
                pass

    if not title:
        title = fp.stem.replace("_", " ").replace("-", " ")
        for prefix in ["lyria ", "minimax ", "youtube "]:
            if title.lower().startswith(prefix):
                title = title[len(prefix):]

    duration = result.get("duration") or _get_duration(str(fp))
    return {
        "track_name": title,
        "track_file": fp.name,
        "track_source": result.get("source", "unknown"),
        "dj_reason": result.get("dj_decision", {}).get("reason", ""),
        "track_start": time.time(),
        "track_duration": duration,
    }


def _auto_pick_timer() -> dict:
    """Ask Gemini to pick optimal timer settings."""
    import json as _json
    context = dj_agent._get_context()

    prompt = """Pick the best Pomodoro preset for right now. Respond JSON only.

Rules:
- Early morning (5-9): Classic 25/5 x4
- Morning (9-12): Deep Work 50/10 x3
- Midday (12-14): Sprint 15/3 x4
- Afternoon (14-17): Classic 25/5 x4 or Deep Work 50/10 x3
- Evening (17-21): Sprint 15/3 x3
- Night (21+): Classic 25/5 x2

Format: {"focus": 25, "break": 5, "cycles": 4, "reason": "why"}"""

    user_msg = f"Time: {context['time_of_day']} ({context['hour']}:00, {context['day_of_week']})"

    try:
        content = dj_agent._chat(prompt, user_msg, max_tokens=150, temperature=0.3)
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return _json.loads(content)
    except Exception:
        return {"focus": 25, "break": 5, "cycles": 4, "reason": "Default classic preset"}


# ─── MCP Tools ───


@mcp.tool()
def set_context(context: str) -> str:
    """Tell the DJ what you're working on so it picks better music and timer.

    Args:
        context: What you're doing, how you're feeling, what phase of work.
    """
    global _user_context
    _user_context = context
    return f"Context set: {context}"


@mcp.tool()
def music(request: str) -> str:
    """Start productivity music with an AI-recommended Pomodoro timer.

    The GLM DJ picks the best music AND timer settings based on:
    - Time of day (morning = deep work, post-lunch = sprints, evening = short)
    - Your request context
    - Neuroscience principles (ultradian rhythms, neural entrainment)

    Music loops continuously. Switches between focus and break music automatically.
    Say "stop" to end.

    IMPORTANT: When calling this tool, include context about what the user is doing
    and how they might be feeling. The DJ uses this to pick better music and timer.

    Args:
        request: Describe what the user wants AND their current context/mood/task.
    """
    global _pomodoro_thread, _current_track

    full_request = f"{request}. User context: {_user_context}" if _user_context else request

    # Signal any existing pomodoro to stop (non-blocking)
    _pomodoro_stop.set()

    # Everything runs in background — return instantly
    def _start():
        global _pomodoro_thread

        # Wait for old pomodoro to finish (in background, not blocking the tool)
        if _pomodoro_thread and _pomodoro_thread.is_alive():
            _pomodoro_thread.join(timeout=5)
        player.stop()

        # Play cached music immediately
        cached = local_cache.list_tracks()
        music_tracks = [t for t in cached if t["format"] == "mp3" and t["size_kb"] > 1000]
        if music_tracks:
            import random
            pick = random.choice(music_tracks)
            player.play_loop(pick["path"])
            with _track_lock:
                _current_track = {
                    "track_name": pick["name"].replace("_", " "),
                    "track_file": pick["name"] + "." + pick["format"],
                    "track_source": "cache",
                    "track_start": time.time(),
                    "track_duration": _get_duration(pick["path"]),
                }
            _write_state()

        _pomodoro_stop.clear()

        # Find real music, pick timer, start pomodoro
        # Pick timer + music in parallel
        timer_result = {}
        music_result = {}

        def _pick_timer():
            timer_result.update(_auto_pick_timer())

        def _pick_music():
            music_result.update(dj_agent.recommend_and_play(full_request))

        t1 = threading.Thread(target=_pick_timer, daemon=True)
        t2 = threading.Thread(target=_pick_music, daemon=True)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=60)

        focus_minutes = timer_result.get("focus", 25)
        break_minutes = timer_result.get("break", 5)
        cycles = timer_result.get("cycles", 4)

        # Swap in real track or show error in status line
        if music_result.get("path"):
            player.play_loop(music_result["path"])
            _set_track(music_result, preserve_pomo=False)
        elif music_result.get("error"):
            # No cached track playing either -- show error
            if not player.is_playing():
                with _track_lock:
                    _current_track = {
                        "track_name": f"Error: {music_result['error'][:50]}",
                        "track_source": "error",
                        "track_start": time.time(),
                        "track_duration": 0,
                    }
                _write_state()
                return  # Don't start pomodoro if no music at all

        # Start pomodoro timer
        phase_end = time.time() + focus_minutes * 60
        _set_pomo_fields("focus", 1, cycles, phase_end, focus_minutes, break_minutes)
        _refresh_quote()

        # Pomodoro loop
        prefetch_q = queue.Queue(maxsize=1)

        def _prefetch(prompt: str):
            r = dj_agent.recommend_and_play(prompt)
            try:
                prefetch_q.put_nowait(r)
            except queue.Full:
                pass

        for cycle in range(cycles):
            if _pomodoro_stop.is_set():
                break

            if cycle > 0:
                player.stop()
                result = dj_agent.recommend_and_play(
                    f"Pomodoro focus {cycle+1}/{cycles}. DIFFERENT style. No vocals, loopable."
                )
                if "path" in result:
                    player.play_loop(result["path"])
                    _set_track(result)

            p_end = time.time() + focus_minutes * 60
            _set_pomo_fields("focus", cycle + 1, cycles, p_end, focus_minutes, break_minutes)
            _refresh_quote()

            # Prefetch, swap every 3 min
            swap_interval = 180
            next_swap = time.time() + swap_interval
            threading.Thread(
                target=_prefetch,
                args=(f"Focus variation {cycle+1}. Different style.",),
                daemon=True,
            ).start()

            while time.time() < p_end and not _pomodoro_stop.is_set():
                if time.time() >= next_swap:
                    try:
                        new_track = prefetch_q.get_nowait()
                        if "path" in new_track:
                            player.play_loop(new_track["path"])
                            _set_track(new_track)
                            _refresh_quote()
                        next_swap = time.time() + swap_interval
                        threading.Thread(
                            target=_prefetch,
                            args=("Another focus variation.",),
                            daemon=True,
                        ).start()
                    except queue.Empty:
                        pass
                _pomodoro_stop.wait(timeout=1)

            if _pomodoro_stop.is_set():
                break

            # Break phase
            player.stop()
            is_long = (cycle + 1) == cycles
            actual_break = break_minutes * 3 if is_long else break_minutes
            phase = "long_break" if is_long else "break"

            result = dj_agent.recommend_and_play(
                f"Pomodoro {'long' if is_long else 'short'} break. Nature sounds, spacious."
            )
            if "path" in result:
                player.play_loop(result["path"])
                _set_track(result)

            p_end = time.time() + actual_break * 60
            _set_pomo_fields(phase, cycle + 1, cycles, p_end, focus_minutes, break_minutes)
            _refresh_quote()

            while time.time() < p_end and not _pomodoro_stop.is_set():
                _pomodoro_stop.wait(timeout=1)

        player.stop()
        _clear_track()

    _pomodoro_thread = threading.Thread(target=_start, daemon=True)
    _pomodoro_thread.start()

    return "Music starting. Say 'stop' to end."


@mcp.tool()
def play_audio(file_path: str, loop: bool = False) -> str:
    """Play a specific audio file.

    Args:
        file_path: Absolute path to the audio file.
        loop: If True, loop the track continuously.
    """
    if loop:
        result = player.play_loop(file_path)
    else:
        result = player.play(file_path, background=True)

    fp = Path(file_path)
    with _track_lock:
        global _current_track
        _current_track = {
            "track_name": fp.stem.replace("_", " "),
            "track_file": fp.name,
            "track_source": "local",
            "track_start": time.time(),
            "track_duration": _get_duration(file_path),
        }
    _write_state()
    return result


@mcp.tool()
def stop() -> str:
    """Stop the currently playing audio and Pomodoro timer."""
    _pomodoro_stop.set()
    player.stop()
    _clear_track()
    return "Audio stopped."


@mcp.tool()
def now_playing() -> str:
    """Check if audio is currently playing."""
    if player.is_playing():
        s = state.read()
        name = s.get("track_name", "Unknown")
        return f"Playing: {name}"
    return "No audio is playing."



@mcp.tool()
def generate_lyria(mood: str = "focus") -> str:
    """Generate music with Google Lyria 3 AI (takes ~10s, produces 30s clips).

    Args:
        mood: One of: focus, pomodoro_focus, pomodoro_break, calm, energize, break, sleep.
    """
    if mood in lyria.MOOD_PROMPTS:
        result = lyria.generate_for_mood(mood)
    else:
        result = lyria.generate(mood, "lyria_custom.mp3")

    if "error" in result:
        return f"Error: {result['error']}"

    player.play(result["path"], background=True)
    _set_track(result, preserve_pomo=False)
    return f"Now playing: {result.get('title', mood)} (Lyria 3)"


@mcp.tool()
def generate_minimax(mood: str = "focus") -> str:
    """Generate music with MiniMax Music 2.5 via GMI Cloud (takes ~30-60s).

    Args:
        mood: One of: focus, calm, energize, break.
    """
    if mood in minimax_music.MOOD_PROMPTS:
        result = minimax_music.generate_for_mood(mood)
    else:
        result = minimax_music.generate(mood, "minimax_custom.mp3")

    if "error" in result:
        return f"Error: {result['error']}"

    player.play(result["path"], background=True)
    _set_track(result, preserve_pomo=False)
    return f"Now playing: {result.get('title', mood)} (MiniMax)"


@mcp.tool()
def play_youtube(query: str) -> str:
    """Search and play audio from YouTube.

    Args:
        query: Search query (e.g., "lo-fi hip hop radio", "ambient focus music").
    """
    result = youtube.search_and_download(query)
    if "error" in result:
        return f"Error: {result['error']}"

    player.play(result["path"], background=True)
    _set_track(result, preserve_pomo=False)
    return f"Now playing: {result.get('title', query)} (YouTube)"


@mcp.tool()
def play_freesound(query: str) -> str:
    """Search and play ambient sounds from Freesound.org.

    Args:
        query: Search query (e.g., "rain ambient", "forest birds", "ocean waves").
    """
    if not freesound.is_available():
        return "Error: FREESOUND_API_KEY not set."

    sounds = freesound.search(query, max_results=1)
    if not sounds or "error" in sounds[0]:
        return f"Error: {sounds[0].get('error', 'No results') if sounds else 'No results'}"

    s = sounds[0]
    result = freesound.download(s["id"], s["preview_url"])
    if "error" in result:
        return f"Error: {result['error']}"

    player.play(result["path"], background=True)
    _set_track(result, preserve_pomo=False)
    return f"Now playing: {s['name']} (Freesound)"


@mcp.tool()
def list_tracks(directory: str | None = None) -> str:
    """List all cached/available audio tracks."""
    tracks = local_cache.list_tracks(directory)
    if not tracks:
        return "No audio files found."
    lines = [f"  {t['name']}.{t['format']} ({t['size_kb']} KB)" for t in tracks]
    return f"Available tracks ({len(tracks)}):\n" + "\n".join(lines)


@mcp.tool()
def list_sources() -> str:
    """List all available music sources and their status."""
    sources = {
        "brainfm": "Available (curated 30-min focus tracks)",
        "lyria3": "Available" if os.environ.get("GOOGLE_API") else "Unavailable (no GOOGLE_API)",
        "youtube": "Available" if youtube.is_available() else "Unavailable (no yt-dlp)",
        "freesound": "Available" if freesound.is_available() else "Unavailable (no FREESOUND_API_KEY)",
        "glm_dj": "Available" if os.environ.get("GMI_INFER") else "Unavailable (no GMI_INFER)",
    }
    lines = [f"  {name}: {status}" for name, status in sources.items()]
    return "Music sources:\n" + "\n".join(lines)


@mcp.tool()
def recommend_session() -> str:
    """Ask the DJ to recommend a Pomodoro preset based on time of day."""
    import json
    context = dj_agent._get_context()

    prompt = """Recommend the best Pomodoro preset. Respond JSON only:
{"preset": "classic|deep_work|sprint", "focus": 25, "break": 5, "cycles": 4, "reason": "why"}"""

    user_msg = f"Time: {context['time_of_day']} ({context['hour']}:00, {context['day_of_week']})"

    try:
        content = dj_agent._chat(prompt, user_msg, max_tokens=150, temperature=0.7)
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        rec = json.loads(content)
        return (
            f"Recommended: {rec.get('preset', 'classic').replace('_', ' ').title()}\n"
            f"Settings: {rec.get('focus', 25)}min focus / {rec.get('break', 5)}min break x {rec.get('cycles', 4)} cycles\n"
            f"Reason: {rec.get('reason', '')}"
        )
    except Exception:
        return "Recommended: Classic Pomodoro (25/5 x 4)"
