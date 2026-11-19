"""Set or check the USB speaker's volume. Chad remembers it across reboots.

    python volume.py 60    set the volume to 60% (0 to 100) and save it
    python volume.py       show the current volume
"""

import sys

from audio import find_usb_card, get_volume, set_volume


def main() -> None:
    card = find_usb_card("aplay")
    if len(sys.argv) < 2:
        print(f"Speaker volume: {get_volume(card)}%")
        return
    try:
        level = int(sys.argv[1])
    except ValueError:
        raise SystemExit("Give a number from 0 to 100, like: python volume.py 60")
    set_volume(card, level)
    print(f"Speaker volume set to {get_volume(card)}% and saved.")


if __name__ == "__main__":
    main()
