"""Procedural audio generation — creates ambient sounds with Python (no API needed)."""

import math
import random
import struct
import wave
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"


def _write_wav(filename: str, frames: list[bytes], sample_rate: int = 44100) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / filename
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"".join(frames))
    return str(path)


def generate_binaural_beats(
    duration: float = 60.0,
    base_freq: float = 200.0,
    beat_freq: float = 10.0,
    amplitude: int = 8000,
) -> dict:
    sample_rate = 44100
    frames_l, frames_r = [], []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        left = amplitude * math.sin(2 * math.pi * base_freq * t)
        right = amplitude * math.sin(2 * math.pi * (base_freq + beat_freq) * t)
        frames_l.append(int(left))
        frames_r.append(int(right))

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"binaural_{int(beat_freq)}hz_{int(duration)}s.wav"
    path = CACHE_DIR / filename
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        for l, r in zip(frames_l, frames_r):
            wf.writeframes(struct.pack("<hh", l, r))

    return {
        "name": filename,
        "path": str(path),
        "source": "procedural",
        "type": "binaural_beats",
    }


def generate_pink_noise(duration: float = 60.0, amplitude: int = 4000) -> dict:
    sample_rate = 44100
    max_key = 0x1F
    key = 0
    white_values = [0.0] * 6
    frames = []
    for i in range(int(sample_rate * duration)):
        last_key = key
        key = (key + 1) & max_key
        diff = last_key ^ key
        for j in range(6):
            if diff & (1 << j):
                white_values[j] = random.uniform(-1.0, 1.0)
        value = sum(white_values) / 6.0
        frames.append(struct.pack("h", int(value * amplitude)))

    filename = f"pink_noise_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav(filename, frames),
        "source": "procedural",
        "type": "pink_noise",
    }


def generate_rain(duration: float = 60.0) -> dict:
    sample_rate = 44100
    frames = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        noise = random.gauss(0, 1)
        mod = (
            0.5
            + 0.3 * math.sin(2 * math.pi * 0.1 * t)
            + 0.2 * math.sin(2 * math.pi * 0.07 * t)
        )
        value = int(noise * 3000 * mod)
        value = max(-32767, min(32767, value))
        frames.append(struct.pack("h", value))

    filename = f"rain_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav(filename, frames),
        "source": "procedural",
        "type": "rain",
    }


def generate_drone(
    duration: float = 60.0,
    base_freq: float = 55.0,
    amplitude: int = 6000,
) -> dict:
    sample_rate = 44100
    frames = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        v = 0.0
        v += math.sin(2 * math.pi * base_freq * t)
        v += 0.5 * math.sin(2 * math.pi * base_freq * 1.5 * t)
        v += 0.3 * math.sin(2 * math.pi * base_freq * 2 * t)
        v += 0.15 * math.sin(2 * math.pi * base_freq * 3 * t)
        mod = 0.7 + 0.3 * math.sin(2 * math.pi * 0.05 * t)
        value = int(v * amplitude * mod / 2)
        value = max(-32767, min(32767, value))
        frames.append(struct.pack("h", value))

    filename = f"drone_{int(base_freq)}hz_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav(filename, frames),
        "source": "procedural",
        "type": "drone",
    }


# Neuroscience-tuned defaults based on brain.fm research:
# - Focus: 16 Hz beta (sweet spot from Nature 2024 study, N=677)
# - Relax/Break: 10 Hz alpha (relaxed wakefulness, recovery)
# - Meditate: 6 Hz theta (deep relaxation, introspection)
# - Sleep: 2 Hz delta (slow-wave sleep induction)
# - Energize: 20 Hz high-beta (alertness, motivation)
MOOD_MAP = {
    "focus": lambda d: generate_binaural_beats(d, beat_freq=16.0),
    "pomodoro_focus": lambda d: generate_binaural_beats(d, beat_freq=16.0),
    "calm": lambda d: generate_drone(d, base_freq=55.0),
    "relax": lambda d: generate_binaural_beats(d, beat_freq=10.0),
    "break": lambda d: generate_binaural_beats(d, beat_freq=10.0),
    "pomodoro_break": lambda d: generate_rain(d),
    "meditate": lambda d: generate_binaural_beats(d, beat_freq=6.0),
    "sleep": lambda d: generate_binaural_beats(d, beat_freq=2.0, base_freq=100.0),
    "rain": lambda d: generate_rain(d),
    "noise": lambda d: generate_pink_noise(d),
    "energize": lambda d: generate_binaural_beats(d, beat_freq=20.0),
}


def generate_for_mood(mood: str, duration: float = 60.0) -> dict:
    gen = MOOD_MAP.get(mood.lower(), MOOD_MAP["focus"])
    return gen(duration)
