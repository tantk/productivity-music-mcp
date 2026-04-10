"""GLM 5.1 DJ Agent — picks music sources and manages the listening experience."""

import json
import os
import time
from datetime import datetime
from openai import OpenAI
from pathlib import Path

from .sources import local_cache, procedural, lyria, minimax_music, freesound, youtube

GMI_BASE_URL = "https://api.gmi-serving.com/v1"
MODEL_CHAIN = [
    "zai-org/GLM-5.1-FP8",
    "zai-org/GLM-5-FP8",
    "deepseek-ai/DeepSeek-V3-0324",
]

_history: list[dict] = []


def _get_client() -> OpenAI:
    return OpenAI(
        api_key=os.environ.get("GMI_INFER", ""),
        base_url=GMI_BASE_URL,
    )


def _get_context() -> dict:
    now = datetime.now()
    hour = now.hour

    if 5 <= hour < 9:
        time_of_day = "early_morning"
    elif 9 <= hour < 12:
        time_of_day = "morning"
    elif 12 <= hour < 14:
        time_of_day = "midday"
    elif 14 <= hour < 17:
        time_of_day = "afternoon"
    elif 17 <= hour < 21:
        time_of_day = "evening"
    else:
        time_of_day = "night"

    available_sources = ["local_cache", "procedural"]
    if os.environ.get("GOOGLE_API"):
        available_sources.append("lyria3")
    if os.environ.get("GMI_INFER"):
        available_sources.append("minimax_music")
    if freesound.is_available():
        available_sources.append("freesound")
    if youtube.is_available():
        available_sources.append("youtube")

    local_tracks = local_cache.list_tracks()

    return {
        "time_of_day": time_of_day,
        "hour": hour,
        "day_of_week": now.strftime("%A"),
        "available_sources": available_sources,
        "local_tracks": [t["name"] for t in local_tracks],
        "recent_history": _history[-5:],
        "procedural_types": ["binaural_beats", "pink_noise", "rain", "drone"],
    }


SYSTEM_PROMPT = """You are a productivity music DJ agent. Your job is to pick the best music for the user based on their mood, task, and context.

You MUST respond with a valid JSON object only — no markdown, no explanation, no text outside the JSON.

Available sources (pick ONE):
- "local_cache": Instant playback from pre-generated files. Best when a matching track already exists.
- "procedural": Python-generated ambient sounds (binaural beats, pink noise, rain, drone). Instant, no API cost. Best for background ambience.
- "lyria3": Google Lyria 3 AI music generation. High quality lo-fi/ambient. Takes ~10s. 30s clips.
- "minimax_music": MiniMax Music 2.5 AI generation via GMI. Good for varied styles. Takes ~30-60s.
- "freesound": Free ambient sounds from freesound.org. Good for nature/ambient. Requires API key.
- "youtube": Download audio from YouTube. Huge library, longer tracks. Takes ~15-30s.

Decision priorities:
1. If a local track matches the mood, use it (instant, no cost)
2. For quick background noise, use procedural (instant, no cost)
3. For high-quality custom music, use lyria3 or minimax_music
4. For specific songs or long sessions, use youtube
5. For nature/ambient sounds, try freesound

JSON response format:
{
  "source": "local_cache|procedural|lyria3|minimax_music|freesound|youtube",
  "action": "play_existing|generate|search|download",
  "params": {
    // source-specific parameters (see below)
  },
  "reason": "Brief explanation of why this choice"
}

Source-specific params:
- local_cache: {"track_name": "partial name match"}
- procedural: {"type": "binaural_beats|pink_noise|rain|drone", "duration": 60, "beat_freq": 14.0}
- lyria3: {"prompt": "detailed music prompt", "mood": "focus|calm|energize|break"}
- minimax_music: {"prompt": "music description", "mood": "focus|calm|energize|break"}
- freesound: {"query": "search terms"}
- youtube: {"query": "search terms"}
"""


def pick(user_request: str) -> dict:
    context = _get_context()
    client = _get_client()

    user_msg = f"""Context:
- Time: {context["time_of_day"]} ({context["hour"]}:00, {context["day_of_week"]})
- Available sources: {", ".join(context["available_sources"])}
- Local tracks: {", ".join(context["local_tracks"]) or "none"}
- Recent history: {json.dumps(context["recent_history"]) if context["recent_history"] else "none"}
- Procedural types: {", ".join(context["procedural_types"])}

User request: {user_request}"""

    last_error = None
    for model in MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=500,
                temperature=0.7,
            )

            content = response.choices[0].message.content
            if not content:
                last_error = f"{model} returned empty response"
                continue

            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

            decision = json.loads(content)
            decision["model"] = model
            return decision

        except json.JSONDecodeError as e:
            last_error = f"{model} returned invalid JSON: {e}"
            continue
        except Exception as e:
            last_error = f"{model} error: {e}"
            continue

    return {
        "source": "procedural",
        "action": "generate",
        "params": {"type": "pink_noise", "duration": 60},
        "reason": f"All DJ models failed ({last_error}), falling back to procedural",
    }


def execute(decision: dict) -> dict:
    source = decision.get("source", "procedural")
    params = decision.get("params", {})

    try:
        if source == "local_cache":
            track_name = params.get("track_name", "")
            track = local_cache.get_track(track_name)
            if track:
                result = track
            else:
                tracks = local_cache.find_by_mood(track_name)
                result = (
                    tracks[0]
                    if tracks
                    else {"error": f"No local track matching '{track_name}'"}
                )

        elif source == "procedural":
            proc_type = params.get("type", "pink_noise")
            duration = params.get("duration", 60)
            if proc_type == "binaural_beats":
                beat_freq = params.get("beat_freq", 14.0)
                result = procedural.generate_binaural_beats(
                    duration=duration, beat_freq=beat_freq
                )
            elif proc_type == "rain":
                result = procedural.generate_rain(duration=duration)
            elif proc_type == "drone":
                base_freq = params.get("base_freq", 55.0)
                result = procedural.generate_drone(
                    duration=duration, base_freq=base_freq
                )
            else:
                result = procedural.generate_pink_noise(duration=duration)

        elif source == "lyria3":
            mood = params.get("mood", "focus")
            prompt = params.get("prompt")
            if prompt:
                result = lyria.generate(prompt, f"lyria_{mood}.mp3")
            else:
                result = lyria.generate_for_mood(mood)

        elif source == "minimax_music":
            mood = params.get("mood", "focus")
            prompt = params.get("prompt")
            if prompt:
                result = minimax_music.generate(prompt, f"minimax_{mood}.mp3")
            else:
                result = minimax_music.generate_for_mood(mood)

        elif source == "freesound":
            query = params.get("query", "ambient")
            sounds = freesound.search(query, max_results=1)
            if sounds and "error" not in sounds[0]:
                s = sounds[0]
                result = freesound.download(s["id"], s["preview_url"])
            else:
                result = sounds[0] if sounds else {"error": "No results from freesound"}

        elif source == "youtube":
            query = params.get("query", "lo-fi focus music instrumental")
            result = youtube.search_and_download(query)

        else:
            result = {"error": f"Unknown source: {source}"}

    except Exception as e:
        result = {"error": f"Execution error: {e}"}

    _history.append(
        {
            "time": datetime.now().isoformat(),
            "source": source,
            "result": result.get("name", result.get("error", "unknown")),
        }
    )

    result["dj_decision"] = decision
    return result


def recommend_and_play(user_request: str) -> dict:
    decision = pick(user_request)
    result = execute(decision)
    return result
