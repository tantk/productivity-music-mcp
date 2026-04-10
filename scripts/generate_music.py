"""
Generate focus/relax/sleep music using Google Lyria 3 via Gemini API.
Based on brain.fm neuroscience research (neural entrainment, beta-wave targeting).

Usage:
    python generate_music.py                    # default: focus, clip (30s)
    python generate_music.py --mode focus       # focus music
    python generate_music.py --mode relax       # relaxation music
    python generate_music.py --mode sleep       # sleep music
    python generate_music.py --mode pomodoro    # pomodoro work session
    python generate_music.py --pro              # use Lyria 3 Pro (~2 min)
    python generate_music.py --prompt "..."     # custom prompt
"""

import argparse
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

from google import genai
from google.genai import types

PRESETS = {
    "focus": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a soothing ambient lo-fi track for deep focus and concentration.
Designed using neuroscience principles: steady-state, low salience, repetitive patterns
that fade into the background and support sustained attention.

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

[0:00 - 0:06] Soft pad fades in with vinyl crackle texture
[0:06 - 0:14] Rhodes piano enters with gentle repeating arpeggio pattern
[0:14 - 0:24] Sub bass and soft brushed percussion add grounding rhythm, guitar weaves in
[0:24 - 0:30] All elements continue at steady state, designed to loop seamlessly

Rules:
- No dynamic changes, no builds, no crescendos, no drops
- No melody that demands attention -- purely background texture
- Every element stays at the same volume throughout
- Repetitive and hypnotic -- designed to support focus, not entertain
- Should feel like warm ambient texture, not foreground music""",
    "relax": """Instrumental only, no vocals, no singing, no lyrics.

Create a calming alpha-wave relaxation track for unwinding after focused work.

Genre: Ambient / nature-inspired
Tempo: 55 BPM or free-flowing, no rigid pulse
Key: F major
Mood: Peaceful, relieving, open, airy, like stepping outside into fresh air

Instruments:
- Gentle wind chimes with long reverb tails
- Soft sustained string pad, very wide stereo
- Warm piano, single isolated notes with lots of space between them
- Subtle nature textures -- distant birds, soft breeze
- No drums, no percussion, no rhythm

[0:00 - 0:08] Soft string pad fades in with gentle breeze texture
[0:08 - 0:18] Piano plays occasional single notes, widely spaced
[0:18 - 0:25] Wind chimes and distant bird sounds add gentle movement
[0:25 - 0:30] Everything slowly thins out, leaving just the pad and breeze

The music should feel like relief -- a complete contrast to focused work.
Spacious, open, unhurried. No urgency whatsoever.""",
    "sleep": """Instrumental only, no vocals, no singing, no lyrics.

Create a deep sleep ambient track targeting delta brainwave states.
Extremely slow evolution, almost static, designed to make the listener feel heavy and drowsy.

Genre: Dark ambient / drone
Tempo: No discernible pulse or rhythm
Key: D minor
Mood: Heavy, dark, enveloping, safe, sinking, like falling into deep water

Instruments:
- Very deep drone bass, almost felt not heard, sub-40Hz
- Dark evolving pad with extremely slow low-pass filter movement
- Occasional distant, heavily reverbed piano note (one every 15-20 seconds)
- Subtle low-frequency rumble like distant ocean or far-away thunder
- No percussion, no rhythm, no bright frequencies

[0:00 - 0:10] Deep drone slowly fades in from silence, very dark
[0:10 - 0:20] Dark pad joins, barely perceptible, filtering very slowly
[0:20 - 0:28] A single distant piano note, drowning in reverb
[0:28 - 0:30] Drone continues, feeling heavier, as if sinking

Everything should feel like it's slowing down and getting heavier.
Volume should feel like it's gradually decreasing.
The listener should feel pulled downward into sleep.""",
    "pomodoro": """Instrumental only, no vocals, no singing, no lyrics, no humming.

Create a perfectly loopable focus music track for a 25-minute Pomodoro work session.
Based on neuroscience: beta-wave entrainment via steady rhythmic patterns,
low salience composition, and consistent sonic texture that supports sustained attention.

Genre: Ambient electronic / lo-fi study beats
Tempo: 72 BPM, 4/4 time
Key: G major
Mood: Focused, determined, warm, steady, like a calm engine running smoothly

Instruments:
- Warm Rhodes piano with subtle tremolo, repeating a simple 2-bar pattern
- Analog synth pad, warm and wide, barely moving
- Lo-fi vinyl crackle and subtle tape warble
- Soft sine sub bass, steady on root notes
- Very gentle brushed hi-hat pattern (straight 8ths, very quiet)
- Soft kick drum, round and deep, on beats 1 and 3

[0:00 - 0:05] Pad and vinyl crackle establish the space
[0:05 - 0:12] Rhodes enters with repeating pattern, sub bass grounds it
[0:12 - 0:25] Brushed hi-hat and kick add subtle forward momentum
[0:25 - 0:30] All elements continue at exact same level -- perfect loop point

Critical: the end must match the beginning exactly for seamless looping.
No variation, no evolution, no builds. Pure steady-state.
This is background infrastructure for the mind, not music to listen to.""",
}


def main():
    parser = argparse.ArgumentParser(description="Generate focus music with Lyria 3")
    parser.add_argument(
        "--mode",
        choices=["focus", "relax", "sleep", "pomodoro"],
        default="focus",
        help="Music mode (default: focus)",
    )
    parser.add_argument(
        "--pro",
        action="store_true",
        help="Use Lyria 3 Pro for longer tracks (~2 min)",
    )
    parser.add_argument(
        "--prompt",
        type=str,
        help="Custom prompt (overrides mode preset)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output filename (default: {mode}-music.mp3)",
    )
    args = parser.parse_args()

    model = "lyria-3-pro-preview" if args.pro else "lyria-3-clip-preview"
    prompt = args.prompt or PRESETS[args.mode]
    filename = args.output or f"{args.mode}-music.mp3"

    client = genai.Client(api_key=os.environ["GOOGLE_API"])

    duration = "~2 min" if args.pro else "30s"
    print(f"Generating {args.mode} music with {model} ({duration})...")

    response = client.models.generate_content(
        model=model,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO", "TEXT"],
        ),
    )

    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)

    if not response.candidates or not response.candidates[0].content.parts:
        print(f"\nGeneration failed or was blocked.")
        if response.candidates:
            print(f"Finish reason: {response.candidates[0].finish_reason}")
        return

    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(f"\n{part.text}")
        elif part.inline_data is not None:
            out_path = output_dir / filename
            with open(out_path, "wb") as f:
                f.write(part.inline_data.data)
            size_kb = out_path.stat().st_size / 1024
            print(f"\nSaved: {out_path} ({size_kb:.0f} KB)")

    print("\nDone!")


if __name__ == "__main__":
    main()
