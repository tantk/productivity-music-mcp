"""Local cache music source — plays pre-generated/downloaded tracks."""

from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".opus"}

CACHE_DIR = Path.home() / ".productivity-music" / "cache"
OUTPUT_DIR = Path.home() / ".productivity-music" / "output"


def list_tracks(directory: str | None = None) -> list[dict]:
    dirs = [Path(directory)] if directory else [CACHE_DIR, OUTPUT_DIR]
    tracks = []
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS:
                tracks.append(
                    {
                        "name": f.stem,
                        "path": str(f),
                        "format": f.suffix.lower().lstrip("."),
                        "size_kb": round(f.stat().st_size / 1024),
                        "source": "local_cache",
                    }
                )
    return tracks


def find_by_mood(mood: str) -> list[dict]:
    tracks = list_tracks()
    mood_lower = mood.lower()
    return [t for t in tracks if mood_lower in t["name"].lower()]


def get_track(name: str) -> dict | None:
    for t in list_tracks():
        if name.lower() in t["name"].lower():
            return t
    return None
