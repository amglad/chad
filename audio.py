"""Mic and speaker helpers for Chad (wraps the arecord/aplay command-line tools)."""

import re
import signal
import subprocess
from pathlib import Path


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
             "-f", "S16_LE", "-r", "16000", "-c", "1", self.path],
            # Hide arecord's harmless "Interrupted system call" note on stop.
            stderr=subprocess.DEVNULL,
        )

    def stop(self) -> None:
        # Same as pressing Ctrl+C on arecord: it finishes the WAV file cleanly.
        self.process.send_signal(signal.SIGINT)
        self.process.wait()


def play(card: int, path: str) -> None:
    subprocess.run(["aplay", "-q", "-D", f"plughw:{card},0", path], check=False)


# ---- Speaker volume ---------------------------------------------------------
# The USB speaker forgets its volume when it's unplugged or the Pi reboots, so
# Chad saves the level in this file and sets it again every time he starts.
VOLUME_FILE = Path(__file__).parent / ".volume"


def _volume_control(card: int) -> str:
    """Find the speaker's volume knob name (often "PCM" or "Speaker")."""
    output = subprocess.run(
        ["amixer", "-c", str(card), "scontrols"],
        capture_output=True, text=True, check=True,
    ).stdout
    # Lines look like: Simple mixer control 'PCM',0
    for name in re.findall(r"'(.+?)',\d+", output):
        info = subprocess.run(
            ["amixer", "-c", str(card), "sget", name], capture_output=True, text=True
        ).stdout
        if "pvolume" in info:  # "pvolume" = has a playback volume
            return name
    raise RuntimeError(f"No volume control found on card {card}:\n{output}")


def get_volume(card: int) -> int:
    """Current speaker volume, 0 to 100."""
    output = subprocess.run(
        ["amixer", "-M", "-c", str(card), "sget", _volume_control(card)],
        capture_output=True, text=True, check=True,
    ).stdout
    match = re.search(r"\[(\d+)%\]", output)
    return int(match.group(1)) if match else 0


def set_volume(card: int, level: int, save: bool = True) -> int:
    """Set the speaker volume (0 to 100) and remember it. Returns the new level."""
    level = max(0, min(100, int(level)))
    control = _volume_control(card)
    # -M uses a volume scale that matches how loud it sounds to your ears.
    subprocess.run(
        ["amixer", "-q", "-M", "-c", str(card), "sset", control, f"{level}%"],
        check=True,
    )
    # Unmute too (some speakers have no mute switch; that's fine).
    subprocess.run(
        ["amixer", "-q", "-c", str(card), "sset", control, "unmute"],
        stderr=subprocess.DEVNULL, check=False,
    )
    if save:
        VOLUME_FILE.write_text(str(level))
    return level


def restore_volume(card: int) -> None:
    """Put the volume back to the last saved level (called when Chad starts)."""
    try:
        if VOLUME_FILE.exists():
            level = set_volume(card, int(VOLUME_FILE.read_text().strip()), save=False)
            print(f"Speaker volume restored to {level}%")
    except Exception as error:
        print(f"(Couldn't restore volume: {error})")
