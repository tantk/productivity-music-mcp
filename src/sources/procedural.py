"""Procedural audio generation — creates ambient sounds with Python (no API needed).

Design principles (informed by brain.fm research & psychoacoustics):
- Fade in/out on every generator to avoid clicks
- Embed binaural beats inside a warm pad, never serve naked sine waves
- Use detuned oscillators and inharmonic partials for organic warmth
- Apply simple single-pole lowpass filtering to remove digital harshness
- Add slow, stochastic modulation so nothing sounds static or periodic
- Generate stereo where it matters (binaural, drone) for immersion
"""

import math
import random
import struct
import wave
from pathlib import Path

CACHE_DIR = Path.home() / ".productivity-music" / "cache"
SAMPLE_RATE = 44100
TWO_PI = 2.0 * math.pi


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def _fade_envelope(i: int, total: int, fade_samples: int) -> float:
    """Compute a fade-in / fade-out multiplier (raised-cosine shape)."""
    if i < fade_samples:
        # fade in: 0 -> 1
        return 0.5 * (1.0 - math.cos(math.pi * i / fade_samples))
    elif i > total - fade_samples:
        # fade out: 1 -> 0
        remaining = total - i
        return 0.5 * (1.0 - math.cos(math.pi * remaining / fade_samples))
    return 1.0


def _soft_clip(x: float) -> float:
    """Soft saturation — tames peaks without hard clipping artifacts."""
    if x > 1.0:
        return 1.0 - 1.0 / (1.0 + x)
    elif x < -1.0:
        return -1.0 + 1.0 / (1.0 - x)
    return x


def _pack_mono(value: float) -> bytes:
    """Pack a -1..1 float to a 16-bit signed sample."""
    s = int(value * 32000)
    s = max(-32767, min(32767, s))
    return struct.pack("<h", s)


def _pack_stereo(left: float, right: float) -> bytes:
    """Pack two -1..1 floats to stereo 16-bit samples."""
    l = max(-32767, min(32767, int(left * 32000)))
    r = max(-32767, min(32767, int(right * 32000)))
    return struct.pack("<hh", l, r)


def _write_wav_mono(filename: str, frames: list[bytes]) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / filename
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return str(path)


def _write_wav_stereo(filename: str, frames: list[bytes]) -> str:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / filename
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(b"".join(frames))
    return str(path)


# ---------------------------------------------------------------------------
# Single-pole lowpass filter (6 dB/octave, very cheap)
# ---------------------------------------------------------------------------

class _LPF:
    """One-pole IIR lowpass.  cutoff_hz sets the -3dB point."""
    __slots__ = ("_a", "_prev")

    def __init__(self, cutoff_hz: float):
        rc = 1.0 / (TWO_PI * cutoff_hz)
        dt = 1.0 / SAMPLE_RATE
        self._a = dt / (rc + dt)
        self._prev = 0.0

    def process(self, x: float) -> float:
        self._prev += self._a * (x - self._prev)
        return self._prev


# ---------------------------------------------------------------------------
# Generators
# ---------------------------------------------------------------------------

def generate_binaural_beats(
    duration: float = 60.0,
    base_freq: float = 110.0,
    beat_freq: float = 10.0,
    amplitude: float = 0.28,
) -> dict:
    """Binaural entrainment embedded in a warm stereo pad.

    Instead of two naked sine waves, we:
    1. Use a lower base frequency (110 Hz = A2) so it's felt, not honky.
    2. Add detuned harmonics to both channels for warmth/richness.
    3. Overlay gentle filtered noise for texture.
    4. Apply slow independent LFO modulation per harmonic so it breathes.
    5. Fade in/out with a raised-cosine envelope.

    The binaural beat is the frequency difference between the two ears'
    fundamentals — the brain perceives it as an amplitude modulation at
    beat_freq Hz, entraining neural oscillations to that rate.
    """
    n_samples = int(SAMPLE_RATE * duration)
    fade_len = int(SAMPLE_RATE * 3.0)  # 3-second fade
    frames = []

    # Noise texture — very gentle, lowpassed
    lpf_noise_l = _LPF(400.0)
    lpf_noise_r = _LPF(400.0)

    # Harmonic ratios and their relative amplitudes (gives a pad-like timbre)
    # Ratios: fundamental, octave, octave+fifth, 2 octaves
    harmonics = [
        (1.0,   1.00),   # fundamental
        (2.0,   0.35),   # octave
        (3.0,   0.12),   # octave + fifth (12th)
        (4.0,   0.06),   # two octaves
    ]

    # Small detuning (in Hz) per harmonic — creates chorus/warmth
    detune = [0.0, 0.3, -0.5, 0.7]

    # Independent LFO speeds per harmonic (very slow)
    lfo_speeds = [0.037, 0.051, 0.023, 0.067]

    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = _fade_envelope(i, n_samples, fade_len)

        left = 0.0
        right = 0.0

        for h_idx, (ratio, amp) in enumerate(harmonics):
            d = detune[h_idx]
            lfo = 0.85 + 0.15 * math.sin(TWO_PI * lfo_speeds[h_idx] * t)

            freq_l = base_freq * ratio + d
            freq_r = (base_freq + beat_freq) * ratio + d

            left  += amp * lfo * math.sin(TWO_PI * freq_l * t)
            right += amp * lfo * math.sin(TWO_PI * freq_r * t)

        # Add filtered noise texture (very subtle)
        noise_l = lpf_noise_l.process(random.gauss(0, 0.08))
        noise_r = lpf_noise_r.process(random.gauss(0, 0.08))
        left  += noise_l
        right += noise_r

        # Apply envelope and amplitude
        left  = _soft_clip(left * amplitude * env)
        right = _soft_clip(right * amplitude * env)

        frames.append(_pack_stereo(left, right))

    filename = f"binaural_{int(beat_freq)}hz_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav_stereo(filename, frames),
        "source": "procedural",
        "type": "binaural_beats",
    }


def generate_pink_noise(duration: float = 60.0, amplitude: float = 0.22) -> dict:
    """Filtered pink noise with gentle breathing modulation.

    Improvements over raw Voss-McCartney:
    1. Lowpass at 1200 Hz — rolls off harsh highs, closer to "brown noise"
       which focus-music users actually prefer.
    2. Slow stochastic amplitude modulation — prevents listener fatigue from
       a perfectly static signal.
    3. Fade in/out.
    """
    n_samples = int(SAMPLE_RATE * duration)
    fade_len = int(SAMPLE_RATE * 2.5)
    frames = []

    # Voss-McCartney state
    max_key = 0x1F
    key = 0
    white_values = [0.0] * 6

    # Lowpass to soften highs
    lpf = _LPF(1200.0)

    # Slow modulation with randomized phase offsets
    mod_phase1 = random.uniform(0, TWO_PI)
    mod_phase2 = random.uniform(0, TWO_PI)
    mod_phase3 = random.uniform(0, TWO_PI)

    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = _fade_envelope(i, n_samples, fade_len)

        # Voss-McCartney pink noise
        last_key = key
        key = (key + 1) & max_key
        diff = last_key ^ key
        for j in range(6):
            if diff & (1 << j):
                white_values[j] = random.uniform(-1.0, 1.0)
        raw = sum(white_values) / 6.0

        # Lowpass filter
        filtered = lpf.process(raw)

        # Slow breathing modulation (three incommensurate rates)
        mod = (0.70
               + 0.15 * math.sin(TWO_PI * 0.062 * t + mod_phase1)
               + 0.10 * math.sin(TWO_PI * 0.031 * t + mod_phase2)
               + 0.05 * math.sin(TWO_PI * 0.017 * t + mod_phase3))

        value = filtered * amplitude * mod * env
        frames.append(_pack_mono(value))

    filename = f"pink_noise_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav_mono(filename, frames),
        "source": "procedural",
        "type": "pink_noise",
    }


def generate_rain(duration: float = 60.0, amplitude: float = 0.25) -> dict:
    """Rain simulation with layered filtered noise.

    Three layers, each lowpassed at different cutoffs, to mimic:
    1. Distant heavy rain (very low rumble, ~200 Hz cutoff)
    2. Nearby steady rain (mid, ~800 Hz cutoff)
    3. Close drips/splatter (higher, ~2500 Hz cutoff, sparser)

    Each layer has independent stochastic modulation so the rain
    feels organic rather than periodic.
    """
    n_samples = int(SAMPLE_RATE * duration)
    fade_len = int(SAMPLE_RATE * 3.0)
    frames = []

    # Three layers with different spectral character
    lpf_low  = _LPF(200.0)
    lpf_mid  = _LPF(800.0)
    lpf_high = _LPF(2500.0)

    # Smoothed modulation envelopes (one per layer)
    mod_lpf_low  = _LPF(0.3)
    mod_lpf_mid  = _LPF(0.5)
    mod_lpf_high = _LPF(0.8)

    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = _fade_envelope(i, n_samples, fade_len)

        # Low rumble layer
        raw_low = random.gauss(0, 1)
        filt_low = lpf_low.process(raw_low)
        mod_low = 0.5 + 0.5 * mod_lpf_low.process(random.gauss(0, 0.5))
        layer_low = filt_low * mod_low * 0.5

        # Mid rain layer
        raw_mid = random.gauss(0, 1)
        filt_mid = lpf_mid.process(raw_mid)
        mod_mid = 0.5 + 0.5 * mod_lpf_mid.process(random.gauss(0, 0.5))
        layer_mid = filt_mid * mod_mid * 0.4

        # High splatter layer (sparser — silence some samples)
        if random.random() < 0.6:
            raw_high = random.gauss(0, 1)
        else:
            raw_high = 0.0
        filt_high = lpf_high.process(raw_high)
        mod_high = 0.3 + 0.7 * mod_lpf_high.process(random.gauss(0, 0.3))
        layer_high = filt_high * mod_high * 0.15

        mixed = (layer_low + layer_mid + layer_high) * amplitude * env
        frames.append(_pack_mono(_soft_clip(mixed)))

    filename = f"rain_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav_mono(filename, frames),
        "source": "procedural",
        "type": "rain",
    }


def generate_drone(
    duration: float = 60.0,
    base_freq: float = 55.0,
    amplitude: float = 0.30,
) -> dict:
    """Warm ambient drone — stereo, detuned, with harmonic breathing.

    This is designed to be a "musical" sound rather than a raw additive patch.

    Key improvements:
    1. Use musically consonant intervals (root, major 3rd, 5th, octave)
       instead of just power-chord fifths. This creates warmth.
    2. Detune each oscillator slightly (1-4 Hz) for analog-synth chorusing.
    3. Each partial has its own independent slow LFO so the timbre evolves
       organically rather than pulsing as one block.
    4. Two sub-bass octaves (heard + felt) for depth.
    5. Gentle lowpass filtering on the upper partials to reduce digital edge.
    6. Stereo: slightly different detuning L vs R for width.
    7. Filtered noise bed for "air" and texture.
    8. Fade in/out.
    """
    n_samples = int(SAMPLE_RATE * duration)
    fade_len = int(SAMPLE_RATE * 4.0)  # 4-second fade
    frames = []

    # Partials: (frequency_ratio, amplitude, detune_L_hz, detune_R_hz, lfo_rate)
    # Tuned to A: root(1), major third(5/4), fifth(3/2), octave(2), high octave(4)
    partials = [
        (0.5,   0.20,  0.0,   0.0,   0.021),  # sub-octave (felt, not heard)
        (1.0,   1.00,  0.0,   0.0,   0.033),  # root (A1 = 55 Hz)
        (1.0,   0.60,  0.7,  -0.7,   0.033),  # root detuned copy (chorus)
        (5/4,   0.30,  0.3,  -0.4,   0.047),  # major third (C#)
        (3/2,   0.35,  -0.5,  0.6,   0.029),  # fifth (E)
        (2.0,   0.25,  0.4,  -0.3,   0.053),  # octave (A2)
        (3.0,   0.08,  -0.2,  0.5,   0.071),  # high fifth (gentle)
    ]

    # LFO phase offsets (randomised so they don't start in sync)
    lfo_phases = [random.uniform(0, TWO_PI) for _ in partials]

    # Noise texture
    noise_lpf_l = _LPF(600.0)
    noise_lpf_r = _LPF(600.0)

    # Overall gentle "breath" LFO
    breath_phase = random.uniform(0, TWO_PI)

    for i in range(n_samples):
        t = i / SAMPLE_RATE
        env = _fade_envelope(i, n_samples, fade_len)

        left = 0.0
        right = 0.0

        for p_idx, (ratio, amp, det_l, det_r, lfo_rate) in enumerate(partials):
            # Each partial has its own slow amplitude modulation
            lfo = 0.75 + 0.25 * math.sin(TWO_PI * lfo_rate * t + lfo_phases[p_idx])

            freq_l = base_freq * ratio + det_l
            freq_r = base_freq * ratio + det_r

            left  += amp * lfo * math.sin(TWO_PI * freq_l * t)
            right += amp * lfo * math.sin(TWO_PI * freq_r * t)

        # Overall breathing modulation (very slow, subtle)
        breath = 0.85 + 0.15 * math.sin(TWO_PI * 0.013 * t + breath_phase)
        left  *= breath
        right *= breath

        # Filtered noise bed
        nl = noise_lpf_l.process(random.gauss(0, 0.06))
        nr = noise_lpf_r.process(random.gauss(0, 0.06))
        left  += nl
        right += nr

        # Normalize, clip, envelope
        # Peak from additive partials can reach ~2.8, so scale down
        scale = amplitude * env / 2.8
        left  = _soft_clip(left * scale)
        right = _soft_clip(right * scale)

        frames.append(_pack_stereo(left, right))

    filename = f"drone_{int(base_freq)}hz_{int(duration)}s.wav"
    return {
        "name": filename,
        "path": _write_wav_stereo(filename, frames),
        "source": "procedural",
        "type": "drone",
    }


# ---------------------------------------------------------------------------
# Mood mapping
# ---------------------------------------------------------------------------
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
    "sleep": lambda d: generate_binaural_beats(d, beat_freq=2.0, base_freq=80.0),
    "rain": lambda d: generate_rain(d),
    "noise": lambda d: generate_pink_noise(d),
    "energize": lambda d: generate_binaural_beats(d, beat_freq=20.0),
}


def generate_for_mood(mood: str, duration: float = 60.0) -> dict:
    gen = MOOD_MAP.get(mood.lower(), MOOD_MAP["focus"])
    return gen(duration)
