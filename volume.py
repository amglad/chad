"""Set or check the USB speaker's volume, and save it so it survives reboots.

    python volume.py 60    set the volume to 60% (0 to 100) and save it
    python volume.py       show the current volume
"""

import re
import subprocess
import sys

from audio import find_usb_card


def playback_control(card: int) -> str:
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
    raise SystemExit(f"Couldn't find a volume control on card {card}:\n{output}")


def current_volume(card: int, control: str) -> str:
    output = subprocess.run(
        ["amixer", "-M", "-c", str(card), "sget", control],
        capture_output=True, text=True, check=True,
    ).stdout
    match = re.search(r"\[(\d+)%\]", output)
    return match.group(1) + "%" if match else "unknown"


def main() -> None:
    card = find_usb_card("aplay")
    control = playback_control(card)

    if len(sys.argv) < 2:
        print(f"Speaker volume: {current_volume(card, control)}")
        return

    try:
        level = int(sys.argv[1])
    except ValueError:
        raise SystemExit("Give a number from 0 to 100, like: python volume.py 60")
    level = max(0, min(100, level))  # keep it in range

    # -M uses a volume scale that matches how loud it sounds to your ears.
    subprocess.run(
        ["amixer", "-q", "-M", "-c", str(card), "sset", control, f"{level}%", "unmute"],
        check=True,
    )
    # Save the mixer settings so they're restored after a reboot.
    subprocess.run(["sudo", "alsactl", "store"], check=False)
    print(f"Speaker volume set to {current_volume(card, control)} and saved.")


if __name__ == "__main__":
    main()
