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

    # Generate a creative title using GLM
    title = _name_track(text_response or prompt)

    return {
        "name": filename,
        "title": title,
        "path": str(out_path),
        "source": "lyria3",
        "size_kb": round(out_path.stat().st_size / 1024),
        "model_response": text_response,
    }


def _name_track(description: str) -> str:
    """Ask Gemini to name the track from its description."""
    api_key = os.environ.get("GOOGLE_API")
    if not api_key:
        return ""
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=description[:300],
            config=types.GenerateContentConfig(
                system_instruction=(
                    "You name music tracks. Given a description, respond with ONLY "
                    "a short creative title (2-5 words). No quotes, no explanation. "
                    "Examples: Midnight Rain, Amber Glow, Still Waters, Quiet Engine, "
                    "Dusk Protocol, Warm Drift, Soft Orbit"
                ),
                max_output_tokens=15,
                temperature=0.9,
            ),
        )
        if response.candidates and response.candidates[0].content.parts:
            title = response.candidates[0].content.parts[0].text.strip().strip('"\'')
            return title if len(title) < 40 else title[:40]
        return ""
    except Exception:
        return ""


MOOD_PROMPTS = {
    "focus": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a steady-state ambient lo-fi track optimized for deep focus and sustained concentration.
Designed using neuroscience principles: low salience, repetitive patterns, beta-wave entrainment support.

Genre: Ambient lo-fi / study music
Tempo: 70 BPM, 4/4 time
Key: C major
Mood: Calm but alert, warm, spacious, hypnotic, unobtrusive

Instruments:
- Warm Rhodes electric piano with subtle tremolo, playing a simple repeating 4-bar arpeggio
- Wide stereo analog synth pad with very slow filter sweep
- Subtle lo-fi vinyl crackle and tape hiss throughout
- Deep sine-wave sub bass on root notes
- Very soft brushed snare and gentle kick, barely audible
- Distant reverbed fingerpicked nylon guitar

[0:00 - 0:06] Soft pad fades in with vinyl crackle
[0:06 - 0:14] Rhodes enters with gentle repeating arpeggio pattern
[0:14 - 0:24] Sub bass and soft brushed percussion, guitar weaves in
[0:24 - 0:30] All elements continue at steady state, seamless loop point

Rules: No dynamic changes, no builds, no crescendos, no drops. Every element stays at the same volume.
Repetitive and hypnotic — designed to fade into the background, not to entertain.""",

    "calm": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a calming alpha-wave track for relaxation and mental recovery after focused work.
Targets alpha brainwave state (8-12 Hz) for relaxed wakefulness.

Genre: Ambient / nature-inspired
Tempo: 55 BPM or free-flowing, no rigid pulse
Key: G major
Mood: Peaceful, relieving, open, airy, like stepping outside into fresh air

Instruments:
- Gentle wind chimes with long reverb tails
- Soft sustained string pad, very wide stereo
- Warm piano, single isolated notes with lots of space between them
- Subtle nature textures — distant birds, soft breeze
- No drums, no percussion, no rhythm

[0:00 - 0:08] Soft string pad fades in with breeze texture
[0:08 - 0:18] Piano plays occasional single notes, widely spaced
[0:18 - 0:25] Wind chimes and distant bird sounds add gentle movement
[0:25 - 0:30] Everything slowly thins, leaving just pad and breeze

Complete contrast to focus music — spacious, open, unhurried. No urgency.""",

    "energize": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create an uplifting electronic track for energy and motivation.
Targets high-beta brainwaves (20-30 Hz) for alertness and drive.

Genre: Future bass / uplifting electronic
Tempo: 118 BPM, 4/4 time
Key: F major
Mood: Determined, positive, forward-moving, bright

Instruments:
- Bright plucked synth lead with rhythmic arpeggios
- Driving four-on-the-floor kick drum, punchy
- Crisp hi-hats with subtle swing
- Warm saw-wave bass, syncopated
- Uplifting chord stabs on off-beats
- Rising filter sweep textures

[0:00 - 0:06] Filtered arpeggios build anticipation
[0:06 - 0:14] Kick and bass drop in, full energy
[0:14 - 0:24] Lead melody rides over the groove, hi-hats open up
[0:24 - 0:30] Full energy maintained, designed to loop

This is for short bursts of motivation — not background focus music.""",

    "break": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a light, cheerful track for a Pomodoro break session (5 minutes).
Should feel like a reward — warm, pleasant, gently stimulating but not demanding.
Targets alpha waves for relaxed recovery.

Genre: Acoustic / light jazz
Tempo: 85 BPM, 4/4 time
Key: D major
Mood: Warm, cozy, cheerful, like a sunny coffee break

Instruments:
- Warm acoustic guitar fingerpicking a simple melody
- Light ukulele strumming on off-beats
- Soft hand percussion — shaker and light bongos
- Round upright bass, walking gently
- Distant melodica or harmonica adding color

[0:00 - 0:06] Acoustic guitar introduces the melody
[0:06 - 0:14] Ukulele and bass join, creating a gentle groove
[0:14 - 0:24] Full arrangement with percussion, melodica adds warmth
[0:24 - 0:30] Settles back to guitar and bass

Light and pleasant — a mental palate cleanser between focus sessions.""",

    "sleep": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a deep sleep ambient track targeting delta brainwaves (0.5-4 Hz).
Extremely slow evolution, almost static, designed to make the listener feel heavy and drowsy.

Genre: Dark ambient / drone
Tempo: No discernible pulse or rhythm
Key: D minor
Mood: Heavy, dark, enveloping, safe, sinking

Instruments:
- Very deep drone bass, sub-40Hz, almost felt not heard
- Dark evolving pad with extremely slow low-pass filter movement
- Occasional distant, heavily reverbed piano note (one every 15-20 seconds)
- Subtle low-frequency rumble like distant ocean
- No percussion, no rhythm, no bright frequencies

[0:00 - 0:10] Deep drone slowly fades in, very dark
[0:10 - 0:20] Dark pad joins, barely perceptible
[0:20 - 0:28] A single distant piano note, drowning in reverb
[0:28 - 0:30] Drone continues, feeling heavier

Everything should feel like it's slowing down and getting heavier.""",

    "pomodoro_focus": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a perfectly loopable focus track for a 25-minute Pomodoro work session.
Based on neuroscience: beta-wave entrainment via steady rhythmic patterns,
low salience composition, consistent sonic texture for sustained attention.

Genre: Ambient electronic / lo-fi study beats
Tempo: 72 BPM, 4/4 time
Key: G major
Mood: Focused, determined, warm, steady, like a calm engine running smoothly

Instruments:
- Warm Rhodes piano with subtle tremolo, repeating a simple 2-bar pattern
- Analog synth pad, warm and wide, barely moving
- Lo-fi vinyl crackle and subtle tape warble
- Soft sine sub bass, steady on root notes
- Very gentle brushed hi-hat (straight 8ths, very quiet)
- Soft kick drum, round and deep, on beats 1 and 3

[0:00 - 0:05] Pad and vinyl crackle establish the space
[0:05 - 0:12] Rhodes enters with repeating pattern, sub bass grounds it
[0:12 - 0:25] Brushed hi-hat and kick add subtle forward momentum
[0:25 - 0:30] All elements continue at exact same level — perfect loop point

Critical: end must match beginning for seamless looping. No variation, no evolution.
Pure steady-state. Background infrastructure for the mind, not music to listen to.""",

    "pomodoro_break": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a refreshing break track for a 5-minute Pomodoro break.
Complete sonic contrast to focus music — signals "break time" to the brain.
Targets alpha waves for rapid mental recovery.

Genre: Ambient nature / light acoustic
Tempo: No fixed tempo, free-flowing
Key: F major
Mood: Relief, fresh air, open space, gentle joy

Instruments:
- Gentle wind chimes, randomly spaced
- Soft acoustic guitar, single notes with reverb
- Nature sounds — birds, gentle stream, leaves rustling
- Warm pad very far in the background
- No drums, no beat, no rhythm

[0:00 - 0:10] Nature sounds fade in — birds, soft breeze
[0:10 - 0:20] Acoustic guitar plays occasional gentle notes
[0:20 - 0:28] Wind chimes add sparkle, stream sounds underneath
[0:28 - 0:30] Gentle fade, leaving just nature

Should feel like stepping outside into a garden. Maximum contrast from focus music.""",
}


def generate_for_mood(mood: str) -> dict:
    prompt = MOOD_PROMPTS.get(mood.lower(), MOOD_PROMPTS["focus"])
    filename = f"lyria_{mood.lower()}.mp3"
    return generate(prompt, filename)
