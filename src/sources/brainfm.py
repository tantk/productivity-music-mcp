"""Brain.fm curated YouTube tracks — neuroscience-backed focus music."""

import random
from . import youtube

# Curated 30-minute focus tracks from brain.fm's official YouTube channel (@brainfmapp)
FOCUS_TRACKS = [
    {"id": "bMEUAVOOAls", "title": "Casting Spells", "tag": "Deep Focus, High Neural Effect"},
    {"id": "Px3-TRXPtws", "title": "Ultraviolets", "tag": "Focus Flow, Medium Neural Effect"},
    {"id": "L9iFUdkIkBE", "title": "Kyoto", "tag": "Intense Focus, High Neural Effect"},
    {"id": "9cRPXoJ6S9E", "title": "Golden Hill", "tag": "Deep Focus, High Neural Effect"},
    {"id": "UpPmnnJcy6A", "title": "Dreamlight", "tag": "Focus, Maximum Concentration"},
    {"id": "5NZ9ZUuSYIE", "title": "Jurisprudence", "tag": "Study, Concentration"},
    {"id": "NHOFkcun06s", "title": "Morning Story", "tag": "Focus, Maximum Concentration"},
    {"id": "8BfboOUWtck", "title": "Groovy Focus Wave", "tag": "Focus, Flow Beats"},
    {"id": "IMerWLNDYxU", "title": "Pomodoro Deep Work", "tag": "30min Pomodoro Session"},
]

SLEEP_TRACKS = [
    {"id": "wdUZNebkdbw", "title": "Deep Sleep", "tag": "Delta Brainwave, 3hr"},
]

# Track which ones have been played to avoid repeats
_played: list[str] = []


def pick_track(mood: str = "focus") -> dict:
    """Pick a brain.fm track, avoiding recent repeats."""
    if mood == "sleep":
        tracks = SLEEP_TRACKS
    else:
        tracks = FOCUS_TRACKS

    # Filter out recently played
    available = [t for t in tracks if t["id"] not in _played]
    if not available:
        _played.clear()
        available = tracks

    track = random.choice(available)
    _played.append(track["id"])

    return track


def download_and_play(mood: str = "focus") -> dict:
    """Pick a brain.fm track from YouTube, download it."""
    track = pick_track(mood)
    url = f"https://www.youtube.com/watch?v={track['id']}"
    filename = f"brainfm_{track['id']}"

    result = youtube.download_audio(url, filename)
    if "error" not in result:
        result["title"] = f"{track['title']} — Brain.fm"
        result["source"] = "brainfm"
        result["tag"] = track["tag"]

    return result
