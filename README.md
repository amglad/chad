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
python3 -m venv .venv          # a private Python install for this project
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

Put those numbers at the top of `scripts/audio_test.py`, then:

```bash
python scripts/audio_test.py
```

It records 3 seconds and plays it back.

## Secrets

API keys live in `.env`, which git ignores. Never commit it. `.env.example` shows what goes in it.
