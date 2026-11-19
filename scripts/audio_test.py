"""Record a few seconds from the USB mic, then play it back on the USB speaker.

Run it from the repo folder:  python scripts/audio_test.py
"""

import re
import subprocess

# ---- Settings ---------------------------------------------------------
# Card numbers for the mic and speaker. Leave as None and the script finds
# the USB devices by itself (USB card numbers can change after a reboot).
# To force a card, put its number here, e.g. MIC_CARD = 1.
MIC_CARD = None
SPEAKER_CARD = None
SECONDS = 3
OUTPUT_FILE = "/tmp/chad_test.wav"
# ----------------------------------------------------------------------


def find_usb_card(list_command: str) -> int:
    """Run `arecord -l` or `aplay -l` and return the first USB card number."""
    output = subprocess.run(
        [list_command, "-l"], capture_output=True, text=True, check=True
    ).stdout
    # Lines look like: "card 1: Device [USB PnP Sound Device], device 0: ..."
    for line in output.splitlines():
        match = re.match(r"card (\d+):", line)
        if match and "USB" in line:
            return int(match.group(1))
    raise SystemExit(
        f"No USB audio card found in `{list_command} -l`. Is it plugged in?\n{output}"
    )


def record(card: int, path: str, seconds: int) -> None:
    # plughw lets ALSA convert the sample rate/format for us.
    subprocess.run(
        [
            "arecord",
            "-D", f"plughw:{card},0",
            "-f", "S16_LE",   # 16-bit samples
            "-r", "16000",    # 16 kHz, what speech-to-text services like
            "-c", "1",        # mono
            "-d", str(seconds),
            path,
        ],
        check=True,  # stop with an error if arecord fails
    )


def play(card: int, path: str) -> None:
    subprocess.run(["aplay", "-D", f"plughw:{card},0", path], check=True)


def main() -> None:
    mic = MIC_CARD if MIC_CARD is not None else find_usb_card("arecord")
    speaker = SPEAKER_CARD if SPEAKER_CARD is not None else find_usb_card("aplay")
    print(f"Using mic on card {mic}, speaker on card {speaker}")

    print(f"Recording for {SECONDS} seconds... talk now!")
    record(mic, OUTPUT_FILE, SECONDS)
    print("Playing it back...")
    play(speaker, OUTPUT_FILE)
    print("Done.")


if __name__ == "__main__":
    main()
