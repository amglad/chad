"""Little sound effects for Chad, made in code (no sound files to download).

ready_chime() returns the path to a UFO-style "I'm ready" chime, creating it
the first time. Run `python sounds.py` to hear it.
"""

import math
import struct
import wave
from pathlib import Path

RATE = 22050  # samples per second
SOUNDS_DIR = Path(__file__).parent / "sounds"


def _ufo_chime():
    """A calm, spooky UFO slowly coming down to land."""
    seconds = 3.0
    total = int(seconds * RATE)
    out = [0.0] * total
    phase_a = phase_b = phase_hum = 0.0

    for i in range(total):
        t = i / RATE
        # Glide down from 1100 Hz to 400 Hz, slowing as it "lands" (ease-out).
        progress = min(1.0, t / 2.4)
        ease = 1 - (1 - progress) ** 3
        pitch = 1100 * (400 / 1100) ** ease
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


def ready_chime() -> str:
    path = SOUNDS_DIR / "ready.wav"
    # Rebuild if missing, or if this file changed since it was made.
    if not path.exists() or path.stat().st_mtime < Path(__file__).stat().st_mtime:
        _write_wav(path, _ufo_chime())
    return str(path)


if __name__ == "__main__":
    from audio import find_usb_card, play

    play(find_usb_card("aplay"), ready_chime())
