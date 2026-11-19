# Chad

A voice-only talking alien plush. Hold the button, talk, let go, and Chad answers out loud.

**Hardware:** Raspberry Pi 3 Model B, USB microphone, USB speaker, push button on GPIO17 (pin 11), power bank.
**Software:** Python on Raspberry Pi OS, with Google Gemini for hearing, answering (with Google Search) and talking.

## How it will work (hold-to-talk)

1. Hold the button: Chad records from the mic.
2. Let go: the recording is sent to speech-to-text.
3. The text goes to a chat model (with Chad's personality).
4. The reply goes to text-to-speech and plays through the speaker.

## Setup on the Pi

```bash
sudo apt update
sudo apt install -y git python3-venv alsa-utils espeak-ng sox
git clone <this repo> ~/chad
cd ~/chad
python3 -m venv --system-site-packages .venv   # project Python that can still see the Pi's GPIO library
source .venv/bin/activate      # turn it on (do this each new terminal)
pip install -r requirements.txt
cp .env.example .env           # then put your Gemini API key in .env
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

## Run Chad

1. Get a free Gemini API key at https://aistudio.google.com/apikey and put it in `.env` as `GEMINI_API_KEY=...`.
2. `source .venv/bin/activate` then `python chad.py`.
3. Hold the button, ask something, let go.

Files: `chad.py` is the main loop, `brain.py` talks to Gemini (the only file to change to switch AI providers), `audio.py` handles the mic and speaker.
Chad's voice comes from Piper (free, runs on the Pi) with an alien effect from `sox`. Change `VOICE_EFFECT` in `.env` to try other sounds. If Piper fails, Chad falls back to the `espeak-ng` robot voice.

## Speaker volume

```bash
python volume.py 60   # set to 60% (0 to 100) and save it
python volume.py      # show the current volume
```

Chad saves the level and sets it again every time he starts. You can also just ask him:
"speak louder", "turn it down", or "volume 70".

## Start Chad automatically at boot

```bash
bash scripts/install_service.sh
```

Chad then starts on every power-up and plays a UFO chime when he's ready.
While the service is running, stop it before running `chad.py` or the test scripts by hand
(they'd fight over the mic and button): `sudo systemctl stop chad`.

- Watch the output: `journalctl -u chad -f`
- After `git pull`: `sudo systemctl restart chad`
- Turn auto-start off: `sudo systemctl disable --now chad`

## Goodnight (voice shutdown)

Hold the button and say "Goodnight, Chad". He says goodbye, plays a UFO take-off chime
and powers the Pi off. Wait for the green light to stop flickering before unplugging.
(This needs Wi-Fi, since Gemini is the one listening.)
