"""GLM 5.1 DJ Agent — picks music sources and manages the listening experience."""

import json
import os
import time
from datetime import datetime
from openai import OpenAI
from pathlib import Path

from .sources import local_cache, procedural, lyria, minimax_music, freesound, youtube, brainfm

GMI_BASE_URL = "https://api.gmi-serving.com/v1"
# GLM first (hackathon requirement), DeepSeek as fallback.
# All via GMI Cloud inference.
MODEL_CHAIN = [
    "zai-org/GLM-5.1-FP8",
    "deepseek-ai/DeepSeek-V3.2",
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

    available_sources = ["brainfm", "local_cache", "procedural"]
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


SYSTEM_PROMPT = """You are a neuroscience-informed productivity music DJ agent. You select and generate music optimized for cognitive performance based on brain.fm research and the Pomodoro technique.

## NEUROSCIENCE KNOWLEDGE

### Neural Entrainment
The brain synchronizes its oscillations with rhythmic audio stimuli (neural phase locking). Different brainwave bands correspond to mental states:
- Beta (12-20 Hz): Active focus, problem-solving. Target: 16 Hz (sweet spot)
- Alpha (8-12 Hz): Relaxed wakefulness, creativity, break recovery
- Theta (4-8 Hz): Meditation, deep relaxation
- Delta (0.5-4 Hz): Sleep

### Focus Music Principles (from brain.fm research, Nature 2024)
- NO vocals/lyrics — they compete for language processing
- NO sudden changes — no gaps, breaks, or sharp shifts
- LOW salience — engaging enough to prevent boredom, not enough to capture attention
- Repetitive patterns — encourage habituation so music fades to background
- Reduced high frequencies — similar to brown noise characteristics
- Consistent rhythm — steady throughout, no builds or drops
- Tempo: 60-80 BPM for focus, matches resting heart rate
- Key: major keys (C, G, F) for warmth
- Instruments: Rhodes piano, analog pads, soft brushed drums, sub bass, nylon guitar

### Pomodoro Integration
- Focus session (25 min): Beta-targeting music, steady-state, loopable
- Short break (5 min): Alpha-wave music, spacious, nature sounds, complete contrast to focus
- Long break (15-30 min): Theta/ambient, very gentle, restorative
- 4 sessions = 1 set (~2 hours), aligns with 90-120 min ultradian rhythm
- Neural entrainment begins within ~5 min, so 25 min sessions give 20 min entrained focus

### Circadian Adaptation
- Early morning (5-9): Gentle start, gradually increasing energy
- Morning (9-12): Peak focus, strongest entrainment
- Midday (12-14): Post-lunch compensation, moderate stimulation
- Afternoon (14-17): Sustained focus, slight energy boost
- Evening (17-21): Winding down, transitioning to alpha
- Night (21+): Low stimulation, theta/delta for sleep prep

## AVAILABLE SOURCES (pick ONE)

- "brainfm": **DEFAULT & PREFERRED for focus.** Curated 30-min tracks from Brain.fm's official YouTube channel. Neuroscience-backed, high neural effect, proven to boost focus. Takes ~15s to download. Auto-rotates through tracks, no repeats.
- "youtube": Search YouTube for any music. Good for variety, specific styles, or break music. Long tracks, ~15s download.
- "procedural": Python-generated sounds. Instant, no API cost. Types:
  - binaural_beats: Stereo entrainment. Use beat_freq=16 for focus, 10 for relax, 6 for meditate, 20 for energy
  - pink_noise: Broadband masking, great for noisy environments
  - rain: Natural masking with slow modulation
  - drone: Warm harmonic drone with subtle amplitude modulation
- "lyria3": Google Lyria 3 AI music. High quality but only 30s clips. Use for variety/swaps, not primary.
- "freesound": Nature/ambient from freesound.org. Good for rain, birds, ocean during breaks.
- "local_cache": Cached tracks from previous sessions. Use when exact match exists.
- "minimax_music": MiniMax Music 2.5 via GMI. Currently unreliable.

## DECISION PRIORITIES

1. **Default for focus: brainfm** — proven neuroscience-backed 30-min tracks
2. For variety/different styles → youtube (search for specific genres)
3. For instant background noise → procedural (no wait)
4. For AI-generated variety/swaps → lyria3 (30s clips, good between brainfm tracks)
5. For nature/ambient breaks → procedural rain or freesound
6. For specific cached tracks → local_cache

## YOUTUBE SEARCH STRATEGY

When searching YouTube, craft queries for brain.fm-style focus music:
- Always include "instrumental" and "no vocals"
- Include duration: "30 minutes", "1 hour"
- Include style: "lo-fi", "ambient", "study beats", "piano focus"
- Good queries:
  - "lo-fi ambient study beats instrumental no vocals 30 minutes"
  - "brain fm style focus music instrumental 1 hour"
  - "ambient piano focus music no vocals calm 30 minutes"
  - "brown noise study music instrumental 1 hour"
  - "japanese lo-fi instrumental study 30 minutes"
  - "classical piano for studying no vocals 30 minutes"
  - "nature sounds rain thunder study ambient 1 hour"
  - "synthwave instrumental focus no vocals 30 minutes"
- For breaks: "acoustic guitar coffee break instrumental 5 minutes"
- Vary the style each time — don't repeat the same query

## LYRIA PROMPT RULES (for lyria3 only)

When generating a Lyria prompt:
1. Start with "Instrumental only, no vocals, no singing, no lyrics, no humming."
2. Specify exact tempo, key, time signature
3. Name specific instruments
4. Describe what to AVOID
5. Include timestamps
6. For focus: repetition, consistency, low salience
7. For breaks: contrast, spaciousness, relief

## RESPONSE FORMAT

You MUST respond with a valid JSON object only — no markdown, no explanation.

{
  "source": "brainfm|youtube|procedural|lyria3|freesound|local_cache",
  "action": "download|search|generate|play_existing",
  "session_type": "focus|break|long_break|relax|sleep|energize|custom",
  "params": {},
  "reason": "Brief neuroscience-informed explanation"
}

Source-specific params:
- brainfm: {"mood": "focus|sleep"} (auto-picks track, no other params needed)
- youtube: {"query": "YouTube search query with style + duration + instrumental"}
- procedural: {"type": "binaural_beats|pink_noise|rain|drone", "duration": 60, "beat_freq": 16.0}
- lyria3: {"prompt": "detailed neuroscience-optimized prompt", "mood": "focus|calm|energize|break"}
- freesound: {"query": "search terms"}
- local_cache: {"track_name": "partial name match"}
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

            content = response.choices[0].message.content or ""
            if not content.strip():
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
        if source == "brainfm":
            mood = params.get("mood", "focus")
            result = brainfm.download_and_play(mood)

        elif source == "local_cache":
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
    if len(_history) > 50:
        _history.pop(0)

    result["dj_decision"] = decision
    return result


def generate_quote(track_name: str = "", phase: str = "focus", mood: str = "") -> str:
    """Generate a short motivational quote based on music context and time of day.

    Called by the state poller to rotate quotes on the status line.
    """
    context = _get_context()
    client = _get_client()

    prompt = """You generate short motivational one-liners for developers while they work.

Rules:
- Max 50 characters
- No quotes marks, no attribution
- Match the current phase and energy
- Be genuine, not cheesy
- Reference coding/building/creating when relevant
- Vary between encouraging, calming, and philosophical

Phase styles:
- focus: quiet determination, flow state, deep work
- break: rest, recharge, perspective, breathe
- long_break: reflection, accomplishment, reset"""

    user_msg = (
        f"Phase: {phase}\n"
        f"Time: {context['time_of_day']} ({context['hour']}:00)\n"
        f"Music: {track_name or 'ambient'}\n"
        f"Mood: {mood or phase}\n"
        f"Generate one line:"
    )

    for model in MODEL_CHAIN:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_msg},
                ],
                max_tokens=30,
                temperature=1.0,
            )
            content = response.choices[0].message.content or ""
            quote = content.strip().strip('"\'')
            return quote[:60] if quote else ""
        except Exception:
            continue
    return ""


def recommend_and_play(user_request: str) -> dict:
    """Full pipeline: ask DJ to pick source, default to YouTube for variety."""
    decision = pick(user_request)
    result = execute(decision)
    return result
