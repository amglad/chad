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


def _tone(seconds, freq_at, volume=0.45, attack=0.03, release=0.15):
    """Make a tone whose pitch follows freq_at(t). Returns a list of samples."""
    samples, phase = [], 0.0
    total = int(seconds * RATE)
    for i in range(total):
        t = i / RATE
        phase += 2 * math.pi * freq_at(t) / RATE
        # Fade in and out so it doesn't click.
        env = min(1.0, t / attack, (seconds - t) / release)
        # A little second harmonic makes it sound less like a plain beep.
        value = math.sin(phase) + 0.25 * math.sin(2 * phase)
        samples.append(volume * env * value / 1.25)
    return samples


def _silence(seconds):
    return [0.0] * int(seconds * RATE)


def _ufo_chime():
    # 1) Theremin-style sweep up with a wobble, like a UFO powering on.
    def sweep(t):
        rise = 350 * (1100 / 350) ** (t / 0.9)       # glide 350 Hz -> 1100 Hz
        return rise * (1 + 0.04 * math.sin(2 * math.pi * 9 * t))  # 9 Hz wobble

    # 2) Two quick "bloops" at the end.
    def bloop(start, end):
        return lambda t: start + (end - start) * (t / 0.12)

    return (
        _tone(0.9, sweep, release=0.25)
        + _silence(0.05)
        + _tone(0.12, bloop(1100, 1500), release=0.06)
        + _silence(0.04)
        + _tone(0.18, bloop(1500, 2000), release=0.12)
    )


def _write_wav(path, samples):
    path.parent.mkdir(exist_ok=True)
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)  # 16-bit
        f.setframerate(RATE)
        f.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in samples))


def ready_chime() -> str:
    path = SOUNDS_DIR / "ready.wav"
    if not path.exists():
        _write_wav(path, _ufo_chime())
    return str(path)


if __name__ == "__main__":
    from audio import find_usb_card, play

    play(find_usb_card("aplay"), ready_chime())
