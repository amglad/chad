"""Little sound effects for Chad, made in code (no sound files to download).

ready_chime() and goodbye_chime() return paths to UFO-style chimes, creating
them the first time. Run `python sounds.py` to hear both.
"""

import math
import struct
import wave
from pathlib import Path

RATE = 22050  # samples per second
SOUNDS_DIR = Path(__file__).parent / "sounds"


def _ufo_chime(start_hz=1100, end_hz=400, seconds=3.0):
    """A calm, spooky UFO. High-to-low = landing, low-to-high = taking off."""
    total = int(seconds * RATE)
    out = [0.0] * total
    phase_a = phase_b = phase_hum = 0.0

    for i in range(total):
        t = i / RATE
        # Glide from start_hz to end_hz, slowing down at the end (ease-out).
        progress = min(1.0, t / (seconds * 0.8))
        ease = 1 - (1 - progress) ** 3
        pitch = start_hz * (end_hz / start_hz) ** ease
        # Slow, wide wobble like an old sci-fi theremin.
        pitch *= 1 + 0.025 * math.sin(2 * math.pi * 5 * t)

        # Two slightly out-of-tune copies "beat" against each other: eerie shimmer.
        phase_a += 2 * math.pi * pitch / RATE
        phase_b += 2 * math.pi * (pitch + 2.5) / RATE
        voice = 0.5 * (math.sin(phase_a) + math.sin(phase_b))

        # Low, slowly pulsing hum underneath (the ship's engine).
        phase_hum += 2 * math.pi * 82 / RATE
        hum = 0.35 * math.sin(phase_hum) * (0.6 + 0.4 * math.sin(2 * math.pi * 0.8 * t))

        # Soft fade in, long gentle fade out.
        env = min(1.0, t / 0.4, (seconds - t) / 1.2)
        out[i] = env * (0.7 * voice + hum)

    # Add a couple of quiet echoes for a spacey feel.
    for delay, level in [(0.22, 0.35), (0.44, 0.15)]:
        d = int(delay * RATE)
        for i in range(total - 1, d - 1, -1):
            out[i] += level * out[i - d]

    peak = max(abs(x) for x in out)
    return [0.45 * x / peak for x in out]


def _write_wav(path, samples):
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)  # 16-bit
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))


def _cached(name, make):
    path = SOUNDS_DIR / name
    # Rebuild if missing, or if this file changed since it was made.
    if not path.exists() or path.stat().st_mtime < Path(__file__).stat().st_mtime:
        _write_wav(path, make())
    return str(path)


def ready_chime() -> str:
    """UFO landing: Chad has booted and is ready to talk."""
    return _cached("ready.wav", _ufo_chime)


def goodbye_chime() -> str:
    """UFO taking off and fading away: Chad is shutting down."""
    return _cached("goodbye.wav", lambda: _ufo_chime(400, 1100, 3.0))


if __name__ == "__main__":
    from audio import find_usb_card, play

    speaker = find_usb_card("aplay")
    print("Ready chime...")
    play(speaker, ready_chime())
    print("Goodbye chime...")
    play(speaker, goodbye_chime())
