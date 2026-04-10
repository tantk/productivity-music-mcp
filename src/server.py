#!/usr/bin/env python3
"""Productivity Music MCP Server — GLM 5.1 DJ-managed, multi-source audio plugin."""

import os
import queue
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
from .sources import local_cache, procedural, lyria, minimax_music, freesound, youtube

mcp = FastMCP("productivity-music")

_pomodoro_stop = threading.Event()
_pomodoro_thread: threading.Thread | None = None
_state_poller: threading.Thread | None = None
_track_lock = threading.Lock()
_current_track: dict = {}


def _start_state_poller():
    """Background thread that updates state file every second while playing."""
    global _state_poller

    if _state_poller and _state_poller.is_alive():
        return  # already running

    def poll():
        last_quote_time = 0
        current_quote = ""
        quote_generating = False

        def _fetch_quote(phase, track):
            nonlocal current_quote, last_quote_time, quote_generating
            try:
                current_quote = dj_agent.generate_quote(track, phase)
                last_quote_time = time.time()
            except Exception:
                pass
            finally:
                quote_generating = False

        while True:
            if _current_track or not _pomodoro_stop.is_set():
                # Read existing state, overlay track info on top
                # This preserves pomo fields written by the pomodoro thread
                existing = state.read()
                with _track_lock:
                    track_copy = dict(_current_track)
                if track_copy:
                    existing.update(track_copy)
                existing["playing"] = True

                # Generate quote in background thread so poller doesn't block
                now = time.time()
                if now - last_quote_time > 60 and not quote_generating:
                    quote_generating = True
                    phase = existing.get("pomo_phase", "focus")
                    track = existing.get("track_name", "")
                    threading.Thread(
                        target=_fetch_quote, args=(phase, track), daemon=True
                    ).start()

                existing["quote"] = current_quote
                state.write(existing)
            time.sleep(1)

    _state_poller = threading.Thread(target=poll, daemon=True)
    _state_poller.start()


# Start poller immediately when server loads
_start_state_poller()


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
    # Fallback: estimate from file size
    fp = Path(file_path)
    sz = fp.stat().st_size
    if fp.suffix == ".wav":
        return sz / (44100 * 2)
    return sz / (128 * 1000 / 8)


def _make_track_info(result: dict) -> dict:
    """Build track info dict from a DJ/source result. Uses title if available."""
    fp = Path(result["path"])
    # Use title from source (YouTube/Lyria provide it)
    title = result.get("title", "")

    if not title:
        # For cached/procedural tracks, generate a name from GLM
        source = result.get("source", "")
        if source in ("local_cache", "procedural", "lyria3"):
            try:
                from .sources.lyria import _name_track
                desc = result.get("model_response", "") or fp.stem
                title = _name_track(desc)
            except Exception:
                pass

    if not title:
        # Final fallback: clean filename
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
    """Ask GLM to pick optimal timer settings based on time of day and context."""
    import json as _json
    context = dj_agent._get_context()
    client = dj_agent._get_client()

    prompt = """Pick the best Pomodoro preset for right now. Respond JSON only.

Rules:
- Early morning (5-9): Classic 25/5 x4 — gentle start
- Morning (9-12): Deep Work 50/10 x3 — peak focus hours
- Midday (12-14): Sprint 15/3 x4 — post-lunch, short bursts
- Afternoon (14-17): Classic 25/5 x4 or Deep Work 50/10 x3
- Evening (17-21): Sprint 15/3 x3 — winding down, shorter
- Night (21+): Classic 25/5 x2 — limited, don't overwork

Format: {"focus": 25, "break": 5, "cycles": 4, "reason": "why"}"""

    user_msg = f"Time: {context['time_of_day']} ({context['hour']}:00, {context['day_of_week']})"

    for model in dj_agent.MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=150,
                temperature=0.3,
            )
            content = response.choices[0].message.content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            return _json.loads(content)
        except Exception:
            continue

    return {"focus": 25, "break": 5, "cycles": 4, "reason": "Default classic preset"}


@mcp.tool()
def music(request: str) -> str:
    """Start productivity music with an AI-recommended Pomodoro timer.

    The GLM DJ picks the best music AND timer settings based on:
    - Time of day (morning = deep work, post-lunch = sprints, evening = short)
    - Your request context
    - Neuroscience principles (ultradian rhythms, neural entrainment)

    Music loops continuously. Switches between focus and break music automatically.
    Say "stop" to end.

    Args:
        request: What you want (e.g., "focus music", "something calm", "lo-fi beats",
                 "I need to concentrate", "play rain sounds").
    """
    global _pomodoro_thread, _current_track

    # Stop anything currently playing
    if not _pomodoro_stop.is_set():
        _pomodoro_stop.set()
        if _pomodoro_thread and _pomodoro_thread.is_alive():
            _pomodoro_thread.join(timeout=5)
    player.stop()
    with _track_lock:
        _current_track = {}

    # Auto-pick timer settings
    timer = _auto_pick_timer()
    focus_minutes = timer.get("focus", 25)
    break_minutes = timer.get("break", 5)
    cycles = timer.get("cycles", 4)
    timer_reason = timer.get("reason", "")

    # Play initial track
    result = dj_agent.recommend_and_play(request)

    if "error" in result:
        return f"Error: {result['error']}\nDJ reasoning: {result.get('dj_decision', {}).get('reason', 'N/A')}"

    track_path = result.get("path")
    if not track_path:
        return f"DJ picked source '{result.get('dj_decision', {}).get('source')}' but no track was produced."

    # Loop the track
    player.play_loop(track_path)
    source = result.get("source", "unknown")
    reason = result.get("dj_decision", {}).get("reason", "")

    with _track_lock:
        _current_track = _make_track_info(result)
        display_name = _current_track["track_name"]

    # Start Pomodoro timer
    _pomodoro_stop.clear()
    phase_end = time.time() + focus_minutes * 60

    # Write initial state with pomodoro
    state.write({
        **_current_track,
        "playing": True,
        "pomo_phase": "focus",
        "pomo_cycle": 1,
        "pomo_total": cycles,
        "pomo_phase_end": phase_end,
        "pomo_focus_min": focus_minutes,
        "pomo_break_min": break_minutes,
    })

    def _set_track(result):
        """Thread-safe track update."""
        if "path" not in result:
            return
        with _track_lock:
            nonlocal _current_track
            _current_track = _make_track_info(result)

    prefetch_q = queue.Queue(maxsize=1)

    def _prefetch(prompt: str):
        """Generate a track in background, put in queue."""
        r = dj_agent.recommend_and_play(prompt)
        try:
            prefetch_q.put_nowait(r)
        except queue.Full:
            pass

    def run_pomodoro():
        global _current_track

        for cycle in range(cycles):
            if _pomodoro_stop.is_set():
                break

            # ─── Focus phase ───
            if cycle > 0:
                player.stop()
                result = dj_agent.recommend_and_play(
                    f"Pomodoro focus session {cycle+1}/{cycles}. "
                    "Generate DIFFERENT focus music than before. "
                    "Beta-wave steady-state, no vocals, loopable. Try a new style or source."
                )
                if "path" in result:
                    player.play_loop(result["path"])
                    _set_track(result)

            p_end = time.time() + focus_minutes * 60
            with _track_lock:
                track_snap = dict(_current_track)
            state.write({
                **track_snap, "playing": True,
                "pomo_phase": "focus", "pomo_cycle": cycle + 1, "pomo_total": cycles,
                "pomo_phase_end": p_end, "pomo_focus_min": focus_minutes,
                "pomo_break_min": break_minutes,
            })

            # Prefetch next track in background, swap every ~3 minutes
            swap_interval = 180
            next_swap = time.time() + swap_interval
            threading.Thread(
                target=_prefetch,
                args=(f"Focus music variation {cycle+1}. Different style. "
                      "Beta-wave, no vocals, steady-state.",),
                daemon=True,
            ).start()

            while time.time() < p_end and not _pomodoro_stop.is_set():
                # Swap in prefetched track?
                if time.time() >= next_swap:
                    try:
                        new_track = prefetch_q.get_nowait()
                        if "path" in new_track:
                            player.play_loop(new_track["path"])
                            _set_track(new_track)
                        next_swap = time.time() + swap_interval
                        threading.Thread(
                            target=_prefetch,
                            args=("Another focus variation. Different style. "
                                  "Beta-wave, no vocals, steady-state.",),
                            daemon=True,
                        ).start()
                    except queue.Empty:
                        pass
                _pomodoro_stop.wait(timeout=1)

            if _pomodoro_stop.is_set():
                break

            # ─── Break phase ───
            player.stop()
            is_long = (cycle + 1) == cycles
            actual_break = break_minutes * 3 if is_long else break_minutes
            phase = "long_break" if is_long else "break"

            result = dj_agent.recommend_and_play(
                f"Pomodoro {'long' if is_long else 'short'} break. "
                "Alpha-wave nature sounds or light acoustic, spacious, relieving."
            )
            if "path" in result:
                player.play_loop(result["path"])
                _set_track(result)

            p_end = time.time() + actual_break * 60
            with _track_lock:
                track_snap = dict(_current_track)
            state.write({
                **track_snap, "playing": True,
                "pomo_phase": phase, "pomo_cycle": cycle + 1, "pomo_total": cycles,
                "pomo_phase_end": p_end, "pomo_focus_min": focus_minutes,
                "pomo_break_min": break_minutes,
            })

            while time.time() < p_end and not _pomodoro_stop.is_set():
                _pomodoro_stop.wait(timeout=1)

        with _track_lock:
            _current_track = {}
        player.stop()
        state.clear()

    _pomodoro_thread = threading.Thread(target=run_pomodoro, daemon=True)
    _pomodoro_thread.start()

    total = cycles * focus_minutes + (cycles - 1) * break_minutes + break_minutes * 3
    return (
        f"Now playing: {display_name}\n"
        f"Source: {source}\n"
        f"DJ reasoning: {reason}\n\n"
        f"Pomodoro: {cycles} x {focus_minutes}min focus / {break_minutes}min break (~{total}min)\n"
        f"Timer reasoning: {timer_reason}\n"
        f"Music loops continuously, switches automatically between focus and break.\n"
        f"Say 'stop' to end."
    )


@mcp.tool()
def play_audio(file_path: str, loop: bool = False) -> str:
    """Play a specific audio file.

    Args:
        file_path: Absolute path to the audio file.
        loop: If True, loop the track continuously.
    """
    if loop:
        return player.play_loop(file_path)
    return player.play(file_path, background=True)


@mcp.tool()
def stop() -> str:
    """Stop the currently playing audio and Pomodoro timer."""
    global _current_track
    _pomodoro_stop.set()
    if _pomodoro_thread and _pomodoro_thread.is_alive():
        _pomodoro_thread.join(timeout=3)
    with _track_lock:
        _current_track = {}
    state.clear()
    return player.stop()


@mcp.tool()
def now_playing() -> str:
    """Check if audio is currently playing."""
    if player.is_playing():
        return "Audio is currently playing."
    return "No audio is playing."


@mcp.tool()
def generate_procedural(sound_type: str = "pink_noise", duration: float = 60.0) -> str:
    """Generate and play a procedural ambient sound (instant, no API needed).

    Args:
        sound_type: One of: binaural_beats, pink_noise, rain, drone
        duration: Duration in seconds (default 60).
    """
    result = procedural.generate_for_mood(sound_type, duration)
    if "error" in result:
        return f"Error: {result['error']}"

    play_result = player.play(result["path"], background=True)
    return f"{play_result} ({result['type']}, {int(duration)}s)"


@mcp.tool()
def generate_lyria(mood: str = "focus") -> str:
    """Generate music with Google Lyria 3 AI (takes ~10s, produces 30s clips).

    Presets are neuroscience-optimized based on brain.fm research:
    - focus: Beta-wave (16Hz) steady-state lo-fi, low salience, loopable
    - pomodoro_focus: Same as focus but optimized for seamless looping
    - pomodoro_break: Alpha-wave nature sounds, contrast to focus
    - calm: Alpha-wave ambient for relaxation
    - break: Light acoustic for Pomodoro breaks
    - sleep: Delta-wave dark ambient drone
    - energize: High-beta uplifting electronic

    Args:
        mood: One of: focus, pomodoro_focus, pomodoro_break, calm, energize, break, sleep. Or a custom prompt.
    """
    if mood in lyria.MOOD_PROMPTS:
        result = lyria.generate_for_mood(mood)
    else:
        result = lyria.generate(mood, "lyria_custom.mp3")

    if "error" in result:
        return f"Error: {result['error']}"

    play_result = player.play(result["path"], background=True)
    return f"{play_result} (Lyria 3, {result.get('size_kb', '?')} KB)"


@mcp.tool()
def generate_minimax(mood: str = "focus") -> str:
    """Generate music with MiniMax Music 2.5 via GMI Cloud (takes ~30-60s).

    Args:
        mood: One of: focus, calm, energize, break. Or a custom prompt.
    """
    if mood in minimax_music.MOOD_PROMPTS:
        result = minimax_music.generate_for_mood(mood)
    else:
        result = minimax_music.generate(mood, "minimax_custom.mp3")

    if "error" in result:
        return f"Error: {result['error']}"

    play_result = player.play(result["path"], background=True)
    return f"{play_result} (MiniMax Music 2.5, {result.get('size_kb', '?')} KB)"


@mcp.tool()
def play_youtube(query: str) -> str:
    """Search and play audio from YouTube.

    Args:
        query: Search query (e.g., "lo-fi hip hop radio", "ambient focus music").
    """
    result = youtube.search_and_download(query)
    if "error" in result:
        return f"Error: {result['error']}"

    play_result = player.play(result["path"], background=True)
    return f"{play_result} (YouTube, {result.get('size_kb', '?')} KB)"


@mcp.tool()
def play_freesound(query: str) -> str:
    """Search and play ambient sounds from Freesound.org.

    Args:
        query: Search query (e.g., "rain ambient", "forest birds", "ocean waves").
    """
    if not freesound.is_available():
        return "Error: FREESOUND_API_KEY not set. Get a free key at https://freesound.org/apiv2/apply/"

    sounds = freesound.search(query, max_results=1)
    if not sounds or "error" in sounds[0]:
        return (
            f"Error: {sounds[0].get('error', 'No results') if sounds else 'No results'}"
        )

    s = sounds[0]
    result = freesound.download(s["id"], s["preview_url"])
    if "error" in result:
        return f"Error: {result['error']}"

    play_result = player.play(result["path"], background=True)
    return f"{play_result} (Freesound: {s['name']}, {s['duration']}s)"


@mcp.tool()
def list_tracks(directory: str | None = None) -> str:
    """List all cached/available audio tracks.

    Args:
        directory: Optional directory to scan. Defaults to cache + output.
    """
    tracks = local_cache.list_tracks(directory)
    if not tracks:
        return "No audio files found."

    lines = []
    for t in tracks:
        lines.append(f"  {t['name']}.{t['format']} ({t['size_kb']} KB) [{t['source']}]")
    return f"Available tracks ({len(tracks)}):\n" + "\n".join(lines)


@mcp.tool()
def list_sources() -> str:
    """List all available music sources and their status."""
    sources = {
        "local_cache": "Available (instant)",
        "procedural": "Available (instant, types: binaural_beats, pink_noise, rain, drone)",
        "lyria3": "Available"
        if os.environ.get("GOOGLE_API")
        else "Unavailable (no GOOGLE_API key)",
        "minimax_music": "Available"
        if os.environ.get("GMI_INFER")
        else "Unavailable (no GMI_INFER key)",
        "freesound": "Available"
        if freesound.is_available()
        else "Unavailable (no FREESOUND_API_KEY)",
        "youtube": "Available"
        if youtube.is_available()
        else "Unavailable (yt-dlp not installed)",
        "glm_dj": "Available"
        if os.environ.get("GMI_INFER")
        else "Unavailable (no GMI_INFER key)",
    }
    lines = [f"  {name}: {status}" for name, status in sources.items()]
    return "Music sources:\n" + "\n".join(lines)


@mcp.tool()
def recommend_session() -> str:
    """Ask the GLM DJ to recommend a Pomodoro preset based on time of day, context, and user history.

    Returns a recommendation with reasoning. The agent should then call
    pomodoro() or music() with the suggested settings.

    The DJ considers:
    - Time of day (morning = Classic, afternoon = Deep Work, late = Sprint)
    - Ultradian rhythms (90-120 min natural focus cycles)
    - Neural entrainment onset (~5 min warmup)
    - User's recent listening history
    """
    import json

    context = dj_agent._get_context()
    client = dj_agent._get_client()

    prompt = """You are a productivity coach. Recommend the best Pomodoro preset for the user right now.

Available presets:
1. Classic Pomodoro: 25 min focus / 5 min break x 4 cycles (100 min total)
   Best for: general tasks, studying, most people. Aligns with ultradian rhythm.

2. Deep Work: 50 min focus / 10 min break x 3 cycles (180 min total)
   Best for: flow-state programming, writing, deep creative work. Longer sessions allow deeper entrainment.

3. Sprint: 15 min focus / 3 min break x 6 cycles (108 min total)
   Best for: tasks you keep avoiding, admin work, emails, low-motivation days.

4. Music Only: No timer, just play focus/calm/sleep/energize music continuously.
   Best for: when you're already in flow and don't want interruptions.

Respond with JSON only:
{
  "preset": "classic|deep_work|sprint|music_only",
  "focus_minutes": 25,
  "break_minutes": 5,
  "cycles": 4,
  "music_mode": "focus",
  "reason": "Why this preset fits right now"
}"""

    user_msg = f"""Context:
- Time: {context['time_of_day']} ({context['hour']}:00, {context['day_of_week']})
- Recent history: {json.dumps(context['recent_history']) if context['recent_history'] else 'none (fresh session)'}

What Pomodoro preset should the user start with?"""

    for model in dj_agent.MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=300,
                temperature=0.7,
            )
            content = response.choices[0].message.content
            if not content:
                continue
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            rec = json.loads(content)

            preset_name = rec.get("preset", "classic")
            focus = rec.get("focus_minutes", 25)
            brk = rec.get("break_minutes", 5)
            cycles = rec.get("cycles", 4)
            reason = rec.get("reason", "")
            mode = rec.get("music_mode", "focus")

            total = cycles * focus + (cycles - 1) * brk + brk * 3
            return (
                f"Recommended: {preset_name.replace('_', ' ').title()}\n"
                f"Settings: {focus}min focus / {brk}min break x {cycles} cycles (~{total}min)\n"
                f"Music mode: {mode}\n"
                f"Reason: {reason}\n\n"
                f"To start, call: pomodoro(focus_minutes={focus}, break_minutes={brk}, cycles={cycles})\n"
                f"Or for music only: music(\"{mode} music\")"
            )
        except Exception:
            continue

    return (
        "Recommended: Classic Pomodoro (default)\n"
        "Settings: 25min focus / 5min break x 4 cycles (~120min)\n"
        "Reason: Safe default backed by research.\n\n"
        "To start, call: pomodoro(focus_minutes=25, break_minutes=5, cycles=4)"
    )


@mcp.tool()
def pomodoro(focus_minutes: int = 25, break_minutes: int = 5, cycles: int = 4) -> str:
    """Start a neuroscience-backed Pomodoro timer with automatic music switching.

    Based on brain.fm research and Pomodoro technique:
    - Focus sessions: Beta-wave (16Hz) music for sustained attention
    - Short breaks: Alpha-wave (10Hz) nature sounds for recovery
    - Long break (after 4 cycles): Theta-wave ambient for deep rest
    - Neural entrainment begins ~5 min in, giving 20 min of entrained focus per session
    - 4 x 25 min = 100 min, aligns with 90-120 min ultradian rhythm

    Args:
        focus_minutes: Focus session length (default 25).
        break_minutes: Break session length (default 5).
        cycles: Number of focus/break cycles (default 4).
    """
    global _pomodoro_thread, _current_track

    if not _pomodoro_stop.is_set() and _pomodoro_thread and _pomodoro_thread.is_alive():
        return "Pomodoro already active. Use stop() to cancel."

    _pomodoro_stop.clear()

    def run_pomodoro():
        global _current_track
        for cycle in range(cycles):
            if _pomodoro_stop.is_set():
                break

            phase_end = time.time() + focus_minutes * 60
            state.write({"playing": True, "pomo_phase": "focus", "pomo_cycle": cycle + 1,
                         "pomo_total": cycles, "pomo_phase_end": phase_end,
                         "pomo_focus_min": focus_minutes, "pomo_break_min": break_minutes})

            result = dj_agent.recommend_and_play(
                f"Pomodoro focus session {cycle+1}/{cycles}. "
                "Beta-wave focus music, no vocals, loopable."
            )
            if "path" in result:
                player.play_loop(result["path"])
                with _track_lock:
                    _current_track = _make_track_info(result)

            while time.time() < phase_end and not _pomodoro_stop.is_set():
                _pomodoro_stop.wait(timeout=1)

            if _pomodoro_stop.is_set():
                break

            player.stop()
            is_long = (cycle + 1) == cycles
            actual_break = break_minutes * 3 if is_long else break_minutes
            phase = "long_break" if is_long else "break"
            phase_end = time.time() + actual_break * 60
            state.write({"playing": True, "pomo_phase": phase, "pomo_cycle": cycle + 1,
                         "pomo_total": cycles, "pomo_phase_end": phase_end,
                         "pomo_focus_min": focus_minutes, "pomo_break_min": break_minutes})

            result = dj_agent.recommend_and_play(
                f"Pomodoro {'long' if is_long else 'short'} break. "
                "Alpha-wave nature sounds, spacious, relieving."
            )
            if "path" in result:
                player.play_loop(result["path"])
                with _track_lock:
                    _current_track = _make_track_info(result)

            while time.time() < phase_end and not _pomodoro_stop.is_set():
                _pomodoro_stop.wait(timeout=1)

        with _track_lock:
            _current_track = {}
        player.stop()
        state.clear()

    _pomodoro_thread = threading.Thread(target=run_pomodoro, daemon=True)
    _pomodoro_thread.start()

    total = cycles * focus_minutes + (cycles - 1) * break_minutes + break_minutes * 3
    return (
        f"Pomodoro started: {cycles} cycles of {focus_minutes}min focus + {break_minutes}min break.\n"
        f"Last break is extended to {break_minutes * 3}min (long break).\n"
        f"Total: ~{total}min. Aligned with ultradian rhythm.\n"
        f"Neural entrainment begins ~5 min into each focus session.\n"
        f"Use stop() to cancel."
    )
