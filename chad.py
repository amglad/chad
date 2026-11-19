"""Chad: hold the button, ask a question, let go, and Chad answers out loud.

Run from the repo folder with the venv on:  python chad.py   (Ctrl+C to quit)
"""

import subprocess
import time

from dotenv import load_dotenv

load_dotenv()  # read GEMINI_API_KEY etc. from .env before brain.py needs them

from gpiozero import Button  # noqa: E402

import audio  # noqa: E402
import brain  # noqa: E402
import sounds  # noqa: E402

BUTTON_PIN = 17      # GPIO17 = physical pin 11
MIN_SECONDS = 0.4    # ignore accidental taps
VOLUME_STEP = 15    # how much "louder" / "quieter" changes the volume
QUESTION_WAV = "/tmp/chad_question.wav"
ANSWER_WAV = "/tmp/chad_answer.wav"


def shut_down(speaker: int) -> None:
    """Say goodbye with the take-off chime and power off the Pi safely."""
    print("Goodnight! Shutting down...")
    subprocess.run(["sync"])  # make sure everything is written to the SD card
    audio.play(speaker, sounds.goodbye_chime())
    # -n: fail instead of waiting for a password nobody can type.
    result = subprocess.run(["sudo", "-n", "systemctl", "poweroff"])
    if result.returncode != 0:
        print("Couldn't power off (sudo needs a password?). Staying on.")
        return
    raise SystemExit(0)


def change_volume(speaker: int, command: str) -> None:
    """Handle VOLUME_UP, VOLUME_DOWN and VOLUME=NN commands."""
    current = audio.get_volume(speaker)
    if command == "VOLUME_UP":
        new = current + VOLUME_STEP
    elif command == "VOLUME_DOWN":
        new = current - VOLUME_STEP
    else:  # "VOLUME=70"
        new = int(command.split("=")[1])
    new = audio.set_volume(speaker, max(new, 10))  # never fully silent by voice
    print(f"Volume {current}% -> {new}%")


def main() -> None:
    mic = audio.find_usb_card("arecord")
    speaker = audio.find_usb_card("aplay")
    button = Button(BUTTON_PIN, bounce_time=0.05)
    recorder = audio.Recorder(mic, QUESTION_WAV)
    audio.restore_volume(speaker)
    brain.warm_up()

    print(f"Chad is ready (chat: {brain.CHAT_MODEL}). Hold the button and talk.")
    audio.play(speaker, sounds.ready_chime())  # UFO chime = ready to talk
    while True:
        button.wait_for_press()
        recorder.start()
        started = time.monotonic()
        print("Listening...")

        button.wait_for_release()
        recorder.stop()
        if time.monotonic() - started < MIN_SECONDS:
            print("Too short, ignored.")
            continue

        try:
            print("Thinking...")
            t0 = time.monotonic()
            with open(QUESTION_WAV, "rb") as f:
                reply = brain.think(f.read())
            reply, commands = brain.split_commands(reply)
            print(f"Chad: {reply}")
            for command in commands:
                if command.startswith("VOLUME"):
                    # Change volume before he answers, so you hear the new level.
                    change_volume(speaker, command)
            t1 = time.monotonic()
            brain.speak(reply, ANSWER_WAV)
            print(f"(think {t1 - t0:.1f}s, voice {time.monotonic() - t1:.1f}s)")
            audio.play(speaker, ANSWER_WAV)
            if "GOODNIGHT" in commands:
                shut_down(speaker)
        except Exception as error:
            # Keep Chad running even if one request fails (Wi-Fi blip, quota, ...).
            print(f"Something went wrong: {error}")
        print("Ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
