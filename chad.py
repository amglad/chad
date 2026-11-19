"""Chad: hold the button, ask a question, let go, and Chad answers out loud.

Run from the repo folder with the venv on:  python chad.py   (Ctrl+C to quit)
"""

import time

from dotenv import load_dotenv

load_dotenv()  # read GEMINI_API_KEY etc. from .env before brain.py needs them

from gpiozero import Button  # noqa: E402

import audio  # noqa: E402
import brain  # noqa: E402

BUTTON_PIN = 17      # GPIO17 = physical pin 11
MIN_SECONDS = 0.4    # ignore accidental taps
QUESTION_WAV = "/tmp/chad_question.wav"
ANSWER_WAV = "/tmp/chad_answer.wav"


def main() -> None:
    mic = audio.find_usb_card("arecord")
    speaker = audio.find_usb_card("aplay")
    button = Button(BUTTON_PIN, bounce_time=0.05)
    recorder = audio.Recorder(mic, QUESTION_WAV)

    print(f"Chad is ready (chat: {brain.CHAT_MODEL}). Hold the button and talk.")
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
            print(f"Chad: {reply}")
            t1 = time.monotonic()
            brain.speak(reply, ANSWER_WAV)
            print(f"(think {t1 - t0:.1f}s, voice {time.monotonic() - t1:.1f}s)")
            audio.play(speaker, ANSWER_WAV)
        except Exception as error:
            # Keep Chad running even if one request fails (Wi-Fi blip, quota, ...).
            print(f"Something went wrong: {error}")
        print("Ready.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBye!")
