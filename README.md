# Chad

A voice-only talking action figure. Hold the button, talk, let go, and Chad answers out loud.

**Hardware:** Raspberry Pi 3 Model B, USB microphone, USB speaker, push button on GPIO17 (pin 11), power bank.
**Software:** Python on Raspberry Pi OS, with a cloud AI for speech-to-text, chat, and text-to-speech.

## How it will work (hold-to-talk)

1. Hold the button: Chad records from the mic.
2. Let go: the recording is sent to speech-to-text.
3. The text goes to a chat model (with Chad's personality).
4. The reply goes to text-to-speech and plays through the speaker.

## Setup on the Pi

```bash
sudo apt update
sudo apt install -y git python3-venv alsa-utils
git clone <this repo> ~/chad
cd ~/chad
python3 -m venv --system-site-packages .venv   # project Python that can still see the Pi's GPIO library
source .venv/bin/activate      # turn it on (do this each new terminal)
pip install -r requirements.txt
cp .env.example .env           # then put your API key in .env
```

## Test the audio

Find your card numbers:

```bash
arecord -l   # microphones
aplay -l     # speakers
```

The script finds the USB cards by itself. To force specific ones, set `MIC_CARD` / `SPEAKER_CARD` at the top of `scripts/audio_test.py`. Run:

```bash
python scripts/audio_test.py
```

It records 3 seconds and plays it back.

## Secrets

API keys live in `.env`, which git ignores. Never commit it. `.env.example` shows what goes in it.

## Test the button

With the button wired (red pin 1, black pin 9, white pin 11):

```bash
python scripts/button_test.py
```

Hold the button and talk, let go, and it plays your voice back. Ctrl+C quits.
