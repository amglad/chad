"""Record a few seconds from the USB mic, then play it back on the USB speaker.

Run it from the repo folder:  python scripts/audio_test.py
"""

import subprocess

# ---- Settings: change these to match your Pi -------------------------
# Card numbers come from `arecord -l` (mic) and `aplay -l` (speaker).
MIC_CARD = 1
SPEAKER_CARD = 2
SECONDS = 3
OUTPUT_FILE = "/tmp/chad_test.wav"
# ----------------------------------------------------------------------


def record(path: str, seconds: int) -> None:
    # plughw lets ALSA convert the sample rate/format for us.
    subprocess.run(
        [
            "arecord",
            "-D", f"plughw:{MIC_CARD},0",
            "-f", "S16_LE",   # 16-bit samples
            "-r", "16000",    # 16 kHz, what speech-to-text services like
            "-c", "1",        # mono
            "-d", str(seconds),
            path,
        ],
        check=True,  # stop with an error if arecord fails
    )


def play(path: str) -> None:
    subprocess.run(["aplay", "-D", f"plughw:{SPEAKER_CARD},0", path], check=True)


def main() -> None:
    print(f"Recording for {SECONDS} seconds... talk now!")
    record(OUTPUT_FILE, SECONDS)
    print("Playing it back...")
    play(OUTPUT_FILE)
    print("Done.")


if __name__ == "__main__":
    main()
