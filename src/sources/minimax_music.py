"""MiniMax Music 2.5 generation via GMI Cloud media API."""

import os
import time
import requests
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"
MEDIA_API_BASE = "https://console.gmicloud.ai/api/v1/ie/requestqueue/apikey"
MODEL_ID = "minimax-music-2.5"


def generate(
    prompt: str, filename: str = "minimax_track.mp3", timeout: int = 120
) -> dict:
    api_key = os.environ.get("GMI_INFER")
    if not api_key:
        return {"error": "GMI_INFER key not set in environment"}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": MODEL_ID,
        "payload": {
            "prompt": prompt,
        },
    }

    resp = requests.post(f"{MEDIA_API_BASE}/requests", headers=headers, json=payload)
    if resp.status_code != 200:
        return {"error": f"Failed to submit job: {resp.status_code} {resp.text[:200]}"}

    data = resp.json()
    request_id = data.get("request_id")
    if not request_id:
        return {"error": f"No request_id in response: {data}"}

    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{MEDIA_API_BASE}/requests/{request_id}", headers=headers)
        if resp.status_code != 200:
            time.sleep(3)
            continue

        status_data = resp.json()
        status = status_data.get("status", "").lower()

        if status == "success":
            outcome = status_data.get("outcome", {})
            audio_url = (
                outcome.get("audio_url")
                or outcome.get("url")
                or outcome.get("video_url")
            )
            if not audio_url:
                for k, v in outcome.items():
                    if isinstance(v, str) and v.startswith("http"):
                        audio_url = v
                        break
            if not audio_url:
                return {"error": f"No audio URL in response: {outcome}"}

            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            out_path = CACHE_DIR / filename
            audio_resp = requests.get(audio_url)
            with open(out_path, "wb") as f:
                f.write(audio_resp.content)

            return {
                "name": filename,
                "path": str(out_path),
                "source": "minimax_music",
                "size_kb": round(out_path.stat().st_size / 1024),
            }

        elif status == "failed":
            return {"error": f"Generation failed: {status_data}"}

        time.sleep(5)

    return {"error": f"Timed out after {timeout}s waiting for generation"}


# MiniMax uses lyrics-style prompts with [inst] tags for instrumental sections.
# Neuroscience-optimized based on brain.fm research.
MOOD_PROMPTS = {
    "focus": (
        "Calm instrumental lo-fi for deep focus. Rhodes piano with subtle tremolo, "
        "warm analog synth pads, vinyl crackle texture, soft brushed drums, sine sub bass. "
        "70 BPM, C major. Steady-state, no changes, no builds, no drops. "
        "Repetitive 4-bar loop, designed to fade into background. No vocals."
    ),
    "pomodoro_focus": (
        "Perfectly loopable focus music for a 25-minute Pomodoro work session. "
        "Rhodes piano repeating simple 2-bar pattern, warm wide pad, vinyl crackle, "
        "gentle brushed hi-hat, soft kick on 1 and 3, sine sub bass. "
        "72 BPM, G major. Pure steady-state — end matches beginning exactly. "
        "No variation, no evolution. Background infrastructure for the mind. No vocals."
    ),
    "calm": (
        "Peaceful ambient for relaxation and recovery. Gentle piano single notes "
        "with lots of space, ethereal string pad, wind chimes with reverb, "
        "nature-inspired textures. 55 BPM, free-flowing. "
        "Spacious, open, unhurried. No drums, no rhythm. No vocals."
    ),
    "pomodoro_break": (
        "Refreshing break music — complete contrast to focused work. "
        "Nature sounds, gentle acoustic guitar, wind chimes, bird songs. "
        "No fixed tempo, free-flowing, F major. "
        "Should feel like stepping outside into fresh air. No vocals."
    ),
    "energize": (
        "Upbeat electronic instrumental for energy and motivation. "
        "Bright plucked synth arpeggios, driving four-on-the-floor kick, "
        "crisp hi-hats, warm saw bass, uplifting chord stabs. "
        "118 BPM, F major. Positive and forward-moving. No vocals."
    ),
    "break": (
        "Light cheerful acoustic for a short Pomodoro break. "
        "Warm fingerpicked acoustic guitar, light ukulele, soft shaker, "
        "round upright bass, distant melodica. 85 BPM, D major. "
        "Warm and cozy, like a sunny coffee break. No vocals."
    ),
    "sleep": (
        "Deep sleep ambient drone. Very deep sub bass drone below 40Hz, "
        "dark evolving pad with extremely slow filter sweep, "
        "occasional distant reverbed piano note every 20 seconds. "
        "No tempo, no rhythm, D minor. Heavy, enveloping, sinking. No vocals."
    ),
}


def generate_for_mood(mood: str) -> dict:
    prompt = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["focus"])
    filename = f"minimax_{mood.lower()}.mp3"
    return generate(prompt, filename)
