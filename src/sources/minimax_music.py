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


MOOD_PROMPTS = {
    "focus": "Calm instrumental lo-fi beat for deep work and concentration. "
    "Soft piano, warm pads, subtle vinyl crackle, 70 BPM, relaxing and steady.",
    "calm": "Peaceful ambient music for relaxation. Gentle strings, soft piano, "
    "nature-inspired textures, 60 BPM, serene and meditative.",
    "energize": "Upbeat electronic instrumental for energy and motivation. "
    "Driving synths, punchy drums, 120 BPM, positive and uplifting.",
    "break": "Light cheerful acoustic instrumental for a short break. "
    "Warm guitar, ukulele, light percussion, 90 BPM, cozy and pleasant.",
}


def generate_for_mood(mood: str) -> dict:
    prompt = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["focus"])
    filename = f"minimax_{mood.lower()}.mp3"
    return generate(prompt, filename)
