"""YouTube audio source via yt-dlp."""

import json as _json
import subprocess
import shutil
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"


def is_available() -> bool:
    return shutil.which("yt-dlp") is not None


def _get_title(url: str) -> str:
    """Get video title without downloading."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "title", "--no-download", "--no-playlist", url],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip() or ""
    except Exception:
        return ""


def download_audio(
    url: str, filename: str | None = None, max_duration: int = 1800
) -> dict:
    if not is_available():
        return {"error": "yt-dlp not installed. Run: pip install yt-dlp"}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Get the actual video title first
    title = _get_title(url)

    fname = filename or "youtube_audio"
    out_path = CACHE_DIR / f"{fname}.%(ext)s"

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format", "mp3",
        "--audio-quality", "5",
        "--max-downloads", "1",
        "--match-filter", f"duration<={max_duration}",
        "--no-playlist",
        "--output", str(out_path),
        url,
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        return {"error": "Download timed out after 120s"}

    # Find the downloaded file
    for f in CACHE_DIR.glob(f"{fname}.*"):
        if f.suffix.lower() in {".mp3", ".m4a", ".opus", ".wav", ".ogg", ".webm"}:
            # Get duration from ffprobe if available
            duration = _get_duration(str(f))
            return {
                "name": f.name,
                "title": title or f.stem,
                "path": str(f),
                "source": "youtube",
                "size_kb": round(f.stat().st_size / 1024),
                "duration": duration,
            }

    return {"error": "Download completed but audio file not found"}


def _get_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", file_path],
            capture_output=True, text=True, timeout=10,
        )
        data = _json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 30))
    except Exception:
        return 30.0


def search_and_download(query: str, filename: str | None = None) -> dict:
    if not is_available():
        return {"error": "yt-dlp not installed. Run: pip install yt-dlp"}

    search_url = f"ytsearch1:{query}"
    fname = filename or query.replace(" ", "_")[:40]
    return download_audio(search_url, fname)


# Curated search queries for neuroscience-appropriate music.
# Brain.fm style: steady-state, no vocals, low salience, repetitive.
MOOD_QUERIES = {
    "focus": "brain fm style focus music instrumental no vocals steady lo-fi ambient 30 minutes",
    "pomodoro_focus": "pomodoro focus music 25 minutes instrumental ambient study beats",
    "calm": "calm ambient piano music peaceful no vocals 30 minutes",
    "relax": "relaxation ambient music alpha waves instrumental 30 minutes",
    "break": "coffee break acoustic instrumental cheerful light 5 minutes",
    "pomodoro_break": "nature sounds birds stream relaxing 5 minutes short",
    "energize": "upbeat instrumental electronic motivation no vocals 30 minutes",
    "sleep": "deep sleep ambient drone delta waves dark 30 minutes",
    "meditate": "theta waves meditation tibetan singing bowls 30 minutes",
    "rain": "rain sounds for studying ambient 30 minutes",
    "noise": "brown noise focus concentration 30 minutes",
    "brainfm": "brain fm neural focus music instrumental steady state ambient",
    "lofi": "lofi hip hop study beats instrumental chill no vocals 30 min",
    "piano": "ambient piano focus music no vocals calm steady 30 minutes",
    "nature": "nature sounds forest birds stream ambient relaxing 30 minutes",
}


def download_for_mood(mood: str) -> dict:
    """Download a YouTube track for a specific mood/session type."""
    query = MOOD_QUERIES.get(mood.lower(), f"{mood} instrumental music no vocals")
    filename = f"youtube_{mood.lower()}"
    return search_and_download(query, filename)
