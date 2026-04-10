#!/usr/bin/env python3
"""Productivity Music MCP Server — GLM 5.1 DJ-managed, multi-source audio plugin."""

import os
import threading
import time
from pathlib import Path
from dotenv import load_dotenv

for env_path in [Path.cwd() / ".env", Path.home() / ".env"]:
    if env_path.exists():
        load_dotenv(env_path)
        break

from mcp.server.fastmcp import FastMCP
from . import player, dj_agent
from .sources import local_cache, procedural, lyria, minimax_music, freesound, youtube

mcp = FastMCP("productivity-music")

_pomodoro_active = False
_pomodoro_thread: threading.Thread | None = None


@mcp.tool()
def music(request: str) -> str:
    """Ask the GLM 5.1 DJ to pick and play music based on your request.

    The AI DJ considers time of day, available sources, listening history,
    and your mood to pick the best music.

    Args:
        request: What you want (e.g., "focus music", "something calm", "I need energy",
                 "play rain sounds", "lo-fi beats for coding").
    """
    result = dj_agent.recommend_and_play(request)

    if "error" in result:
        return f"Error: {result['error']}\nDJ reasoning: {result.get('dj_decision', {}).get('reason', 'N/A')}"

    track_path = result.get("path")
    if not track_path:
        return f"DJ picked source '{result.get('dj_decision', {}).get('source')}' but no track was produced."

    play_result = player.play(track_path, background=True)
    source = result.get("source", "unknown")
    reason = result.get("dj_decision", {}).get("reason", "")

    return f"{play_result}\nSource: {source}\nDJ reasoning: {reason}"


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
    """Stop the currently playing audio."""
    global _pomodoro_active
    _pomodoro_active = False
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

    Args:
        mood: One of: focus, calm, energize, break. Or a custom prompt.
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
def pomodoro(focus_minutes: int = 25, break_minutes: int = 5, cycles: int = 4) -> str:
    """Start a Pomodoro timer with automatic music switching.

    Plays focus music during work, break music during breaks.

    Args:
        focus_minutes: Focus session length (default 25).
        break_minutes: Break session length (default 5).
        cycles: Number of focus/break cycles (default 4).
    """
    global _pomodoro_active, _pomodoro_thread

    if _pomodoro_active:
        return "Pomodoro already active. Use stop() to cancel."

    _pomodoro_active = True

    def run_pomodoro():
        global _pomodoro_active
        for cycle in range(cycles):
            if not _pomodoro_active:
                break

            result = dj_agent.recommend_and_play(
                "deep focus music for concentrated work"
            )
            if "path" in result:
                player.play_loop(result["path"])

            for _ in range(focus_minutes * 60):
                if not _pomodoro_active:
                    return
                time.sleep(1)

            if not _pomodoro_active:
                break

            player.stop()
            result = dj_agent.recommend_and_play("light upbeat music for a short break")
            if "path" in result:
                player.play(result["path"], background=True)

            for _ in range(break_minutes * 60):
                if not _pomodoro_active:
                    return
                time.sleep(1)

        _pomodoro_active = False
        player.stop()

    _pomodoro_thread = threading.Thread(target=run_pomodoro, daemon=True)
    _pomodoro_thread.start()

    return (
        f"Pomodoro started: {cycles} cycles of {focus_minutes}min focus + {break_minutes}min break.\n"
        f"Total: {cycles * (focus_minutes + break_minutes)}min. Use stop() to cancel."
    )
