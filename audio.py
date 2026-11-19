"""Mic and speaker helpers for Chad (wraps the arecord/aplay command-line tools)."""

import re
import subprocess


def find_usb_card(list_command: str) -> int:
    """Run `arecord -l` or `aplay -l` and return the first USB card number."""
    output = subprocess.run(
        [list_command, "-l"], capture_output=True, text=True, check=True
    ).stdout
    for line in output.splitlines():
        match = re.match(r"card (\d+):", line)
        if match and "USB" in line:
            return int(match.group(1))
    raise SystemExit(f"No USB audio card in `{list_command} -l`. Plugged in?\n{output}")


class Recorder:
    """Start recording with start(), stop it with stop(). Records 16 kHz mono WAV."""

    def __init__(self, card: int, path: str):
        self.card = card
        self.path = path
        self.process = None

    def start(self) -> None:
        # No -d (duration), so arecord runs until we stop it.
        self.process = subprocess.Popen(
            ["arecord", "-q", "-D", f"plughw:{self.card},0",
             "-f", "S16_LE", "-r", "16000", "-c", "1", self.path]
        )

    def stop(self) -> None:
        self.process.terminate()  # same as pressing Ctrl+C on arecord
        self.process.wait()


def play(card: int, path: str) -> None:
    subprocess.run(["aplay", "-q", "-D", f"plughw:{card},0", path], check=False)
