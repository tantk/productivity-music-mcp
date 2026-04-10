"""Freesound.org ambient sound source (free API, optional key)."""

import os
import requests
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"
API_BASE = "https://freesound.org/apiv2"


def _get_key() -> str | None:
    return os.environ.get("FREESOUND_API_KEY")


def is_available() -> bool:
    return _get_key() is not None


def search(query: str, max_results: int = 5) -> list[dict]:
    key = _get_key()
    if not key:
        return [
            {
                "error": "FREESOUND_API_KEY not set. Get one free at https://freesound.org/apiv2/apply/"
            }
        ]

    params = {
        "query": query,
        "token": key,
        "fields": "id,name,duration,previews,tags,avg_rating",
        "page_size": max_results,
        "sort": "rating_desc",
        "filter": "duration:[10 TO 300]",
    }

    resp = requests.get(f"{API_BASE}/search/text/", params=params)
    if resp.status_code != 200:
        return [{"error": f"Freesound API error: {resp.status_code}"}]

    results = []
    for sound in resp.json().get("results", []):
        previews = sound.get("previews", {})
        results.append(
            {
                "id": sound["id"],
                "name": sound["name"],
                "duration": round(sound.get("duration", 0), 1),
                "preview_url": previews.get("preview-hq-mp3")
                or previews.get("preview-lq-mp3"),
                "rating": sound.get("avg_rating", 0),
                "source": "freesound",
            }
        )
    return results


def download(sound_id: int, preview_url: str, filename: str | None = None) -> dict:
    if not preview_url:
        return {"error": "No preview URL provided"}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fname = filename or f"freesound_{sound_id}.mp3"
    out_path = CACHE_DIR / fname

    resp = requests.get(preview_url)
    if resp.status_code != 200:
        return {"error": f"Download failed: {resp.status_code}"}

    with open(out_path, "wb") as f:
        f.write(resp.content)

    return {
        "name": fname,
        "path": str(out_path),
        "source": "freesound",
        "size_kb": round(out_path.stat().st_size / 1024),
    }


MOOD_QUERIES = {
    "focus": "ambient background noise office",
    "calm": "nature rain forest peaceful",
    "energize": "upbeat electronic loop",
    "break": "birds chirping nature morning",
    "rain": "rain thunderstorm ambient",
    "ocean": "ocean waves beach",
}


def search_for_mood(mood: str) -> list[dict]:
    query = MOOD_QUERIES.get(mood.lower(), f"{mood} ambient")
    return search(query)
