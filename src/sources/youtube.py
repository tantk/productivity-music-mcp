"""YouTube audio source via yt-dlp."""

import subprocess
import shutil
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"


def is_available() -> bool:
    return shutil.which("yt-dlp") is not None


def download_audio(
    url: str, filename: str | None = None, max_duration: int = 600
) -> dict:
    if not is_available():
        return {"error": "yt-dlp not installed. Run: pip install yt-dlp"}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fname = filename or "youtube_audio"
    out_path = CACHE_DIR / f"{fname}.%(ext)s"

    cmd = [
        "yt-dlp",
        "--extract-audio",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "5",
        "--max-downloads",
        "1",
        "--match-filter",
        f"duration<={max_duration}",
        "--no-playlist",
        "--output",
        str(out_path),
        url,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            return {"error": f"yt-dlp failed: {result.stderr[:300]}"}
    except subprocess.TimeoutExpired:
        return {"error": "Download timed out after 120s"}

    for f in CACHE_DIR.glob(f"{fname}.*"):
        if f.suffix.lower() in {".mp3", ".m4a", ".opus", ".wav", ".ogg"}:
            return {
                "name": f.name,
                "path": str(f),
                "source": "youtube",
                "size_kb": round(f.stat().st_size / 1024),
            }

    return {"error": "Download completed but audio file not found"}


def search_and_download(query: str, filename: str | None = None) -> dict:
    if not is_available():
        return {"error": "yt-dlp not installed. Run: pip install yt-dlp"}

    search_url = f"ytsearch1:{query}"
    fname = filename or query.replace(" ", "_")[:40]
    return download_audio(search_url, fname)


MOOD_QUERIES = {
    "focus": "lo-fi beats to study relax instrumental",
    "calm": "calm ambient music peaceful relaxation instrumental",
    "energize": "upbeat instrumental music energy motivation",
    "break": "happy acoustic instrumental music coffee break",
}


def download_for_mood(mood: str) -> dict:
    query = MOOD_QUERIES.get(mood.lower(), f"{mood} instrumental music")
    filename = f"youtube_{mood.lower()}"
    return search_and_download(query, filename)
