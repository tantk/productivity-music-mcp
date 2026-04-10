"""Google Lyria 3 music generation source."""

import os
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"


def generate(prompt: str, filename: str = "lyria_track.mp3") -> dict:
    api_key = os.environ.get("GOOGLE_API")
    if not api_key:
        return {"error": "GOOGLE_API key not set in environment"}

    try:
        from google import genai
        from google.genai import types
    except ImportError:
        return {
            "error": "google-genai package not installed. Run: pip install google-genai"
        }

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="lyria-3-clip-preview",
        contents=prompt,
        config=types.GenerateContentConfig(response_modalities=["AUDIO", "TEXT"]),
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    out_path = CACHE_DIR / filename

    text_response = None
    for part in response.parts:
        if part.text is not None:
            text_response = part.text
        elif part.inline_data is not None:
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)

    if not out_path.exists():
        return {"error": f"Lyria 3 did not return audio. Response: {text_response}"}

    return {
        "name": filename,
        "path": str(out_path),
        "source": "lyria3",
        "size_kb": round(out_path.stat().st_size / 1024),
        "model_response": text_response,
    }


MOOD_PROMPTS = {
    "focus": """Instrumental only, no vocals, no singing, no lyrics.
Soothing ambient lo-fi track for deep focus and concentration.
Genre: Lo-fi ambient / chillhop. Tempo: 70 BPM. Key: C major.
Soft Rhodes piano, warm analog synth pads, subtle vinyl crackle,
light fingerpicked acoustic guitar, soft brushed drums, deep warm sub bass.""",
    "calm": """Instrumental only, no vocals, no singing, no lyrics.
Peaceful ambient music for relaxation and calm.
Genre: Ambient. Tempo: 60 BPM. Key: G major.
Gentle piano arpeggios, ethereal pad textures, soft string drones,
nature-inspired textures, minimal percussion.""",
    "energize": """Instrumental only, no vocals, no singing, no lyrics.
Upbeat electronic track for energy and motivation.
Genre: Future bass / electronic. Tempo: 120 BPM. Key: F major.
Punchy synth leads, driving bass, crisp hi-hats, uplifting chord progression,
rhythmic arpeggios, building energy throughout.""",
    "break": """Instrumental only, no vocals, no singing, no lyrics.
Light and cheerful acoustic track for a relaxing break.
Genre: Acoustic / folk. Tempo: 90 BPM. Key: D major.
Warm acoustic guitar fingerpicking, light ukulele, soft hand percussion,
gentle bass, warm and cozy atmosphere.""",
}


def generate_for_mood(mood: str) -> dict:
    prompt = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["focus"])
    filename = f"lyria_{mood.lower()}.mp3"
    return generate(prompt, filename)
