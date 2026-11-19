"""Hold the button to record, let go to hear it played back.

Wiring: red -> pin 1 (3.3V), black -> pin 9 (GND), white -> pin 11 (GPIO17).
Run it from the repo folder:  python scripts/button_test.py   (Ctrl+C to quit)
"""

import signal
import subprocess
import sys
import time
from pathlib import Path

from gpiozero import Button

# Reuse the USB card finder from the audio test.
sys.path.insert(0, str(Path(__file__).parent))
from audio_test import find_usb_card  # noqa: E402

BUTTON_PIN = 17  # GPIO number (not the physical pin number)
RECORDING = "/tmp/chad_button.wav"
MIN_SECONDS = 0.3  # ignore accidental taps shorter than this


def main() -> None:
    mic = find_usb_card("arecord")
    speaker = find_usb_card("aplay")
    # Pressing connects GPIO17 to ground; bounce_time filters contact chatter.
    button = Button(BUTTON_PIN, bounce_time=0.05)

    print("Ready. Hold the button and talk. Ctrl+C to quit.")
    while True:
        button.wait_for_press()
        print("Recording...")
        started = time.monotonic()
        # No -d (duration), so arecord keeps going until we stop it.
        recorder = subprocess.Popen(
            ["arecord", "-q", "-D", f"plughw:{mic},0",
             "-f", "S16_LE", "-r", "16000", "-c", "1", RECORDING]
        )

        button.wait_for_release()
        recorder.send_signal(signal.SIGINT)  # like pressing Ctrl+C on arecord
        recorder.wait()
        held = time.monotonic() - started

        if held < MIN_SECONDS:
            print("Too short, ignored.")
            continue
        print(f"Got {held:.1f}s. Playing back...")
        subprocess.run(["aplay", "-q", "-D", f"plughw:{speaker},0", RECORDING])
        print("Ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
