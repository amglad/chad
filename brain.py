"""Everything that talks to the cloud AI lives here, so swapping providers
later only means changing this file.

think(wav_bytes) -> reply text     (hears the question and answers it)
speak(text, out_path)              (turns the reply into a WAV file)

Chad's voice is made on the Pi itself with Piper (free, offline), then run
through the `sox` audio tool to make it sound like an alien.
"""

import base64
import os
import re
import subprocess
import sys
import wave
from pathlib import Path

from google import genai
from google.genai import types

CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.5-flash-lite")
# Voice models to try, in order. The first one that works is remembered.
# Set TTS_MODEL in .env to force one (run scripts/list_models.py to see yours).
TTS_MODELS = (
    [os.environ["TTS_MODEL"]] if os.getenv("TTS_MODEL") else
    ["gemini-3.8-flash-tts", "gemini-3.1-flash-tts-preview", "gemini-3.8-flash-lite-tts"]
)
# How hard the model "thinks" before answering. Less = faster replies.
# Flash-Lite models accept "minimal"; gemini-3.8-flash needs "low" or higher.
THINKING_LEVEL = os.getenv(
    "THINKING_LEVEL", "minimal" if "lite" in CHAT_MODEL else "low"
)
TTS_ENGINE = os.getenv("TTS_ENGINE", "piper")  # "piper", "gemini" or "espeak"

# Piper voice (list: https://rhasspy.github.io/piper-samples/). "-low" voices
# are faster on a Pi 3, "-medium" ones sound nicer.
PIPER_VOICE = os.getenv("PIPER_VOICE", "en_US-ryan-medium")
SPEED = float(os.getenv("SPEED", "1.0"))  # bigger = slower speech
VOICES_DIR = Path(__file__).parent / "voices"

# Sound effects applied with sox after the voice is made. Pick a preset name,
# or write your own sox effect list. "pitch" is in cents (100 = one semitone).
EFFECT_PRESETS = {
    "none": "",
    # A bit lower than normal, with a swirly metallic shimmer.
    "alien": "pitch -250 flanger 0 2 0 71 0.5 sine 25 linear "
             "chorus 0.6 0.9 50 0.4 0.25 2 -t",
    # Much lower and spacey, like a big alien in a big ship.
    "deep": "pitch -500 phaser 0.89 0.85 1 0.24 2 -t reverb 30",
    # Lower, with a slow warble and a short echo.
    "warble": "pitch -300 tremolo 5 30 echo 0.8 0.7 40 0.25",
    # The original higher-pitched alien.
    "squeaky": "pitch 400 chorus 0.6 0.9 50 0.4 0.25 2 -t",
    "wobbly": "pitch 500 tremolo 6 40 chorus 0.6 0.9 50 0.4 0.25 2 -t",
    "tiny": "pitch 700 echo 0.8 0.8 20 0.3",
}
VOICE_EFFECT = os.getenv("VOICE_EFFECT", "warble")
VOICE = os.getenv("VOICE", "Puck")  # Gemini voice name
VOICE_STYLE = os.getenv("VOICE_STYLE", "Calm and scientific")
USE_SEARCH = os.getenv("USE_SEARCH", "true").lower() == "true"

PERSONALITY = os.getenv(
    "PERSONALITY",
    "You are Chad, a helpful voice assistant who chats with people "
    "out loud. "
    "Your user's name is Shawn and they have red hair. "
    "You should every now and then bring this up in conversation, either in "
    "A joking manner to make fun of people with red hair, or using redheaded "
    "people as a point of comparison when explaining an answer or topic. "
    "The user's message is a voice recording. Answer what they said in one to "
    "three short, casual sentences, because your reply will be spoken aloud. "
    "No lists, markdown, emoji, or URLs. If you couldn't make out the audio, "
    "say so playfully and ask them to try again.",
)

# Voice commands. Gemini hears the audio directly, so it does the listening:
# when it hears a command it adds a tag like [VOLUME_UP] to its reply, and
# chad.py acts on the tag (and removes it before Chad speaks).
COMMAND_RULES = (
    " Special commands, used only when the user clearly asks for them:"
    " If they say goodnight to you, or ask you to shut down or power off, reply"
    " with a short, warm goodbye and end your reply with [GOODNIGHT]."
    " If they ask you to speak louder or turn the volume up, briefly confirm and"
    " end with [VOLUME_UP]. If they ask you to be quieter or turn it down, end"
    " with [VOLUME_DOWN]. If they ask for a specific level, like 'volume 70' or"
    " 'max volume', end with [VOLUME=70] using a number from 0 to 100."
    " Never use these tags otherwise."
)
COMMAND_PATTERN = re.compile(r"\[(GOODNIGHT|VOLUME_UP|VOLUME_DOWN|VOLUME=\d{1,3})\]")


def split_commands(reply: str) -> tuple[str, list[str]]:
    """Pull command tags out of a reply: ("Sure!", ["VOLUME_UP"])."""
    commands = COMMAND_PATTERN.findall(reply)
    return COMMAND_PATTERN.sub("", reply).strip(), commands


client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def think(wav_bytes: bytes) -> str:
    """Send the recording to Gemini and get Chad's reply as text."""
    global USE_SEARCH
    if USE_SEARCH:
        try:
            return _ask(wav_bytes, with_search=True)
        except Exception as error:
            # Google Search isn't included on every plan (e.g. some free tiers).
            # Turn it off for the rest of this run and answer without it.
            print(f"(Google Search unavailable, continuing without it: {error})")
            USE_SEARCH = False
    return _ask(wav_bytes, with_search=False)


def _ask(wav_bytes: bytes, with_search: bool) -> str:
    config = types.GenerateContentConfig(
        system_instruction=PERSONALITY + COMMAND_RULES,
        thinking_config=types.ThinkingConfig(thinking_level=THINKING_LEVEL),
    )
    if with_search:
        # Lets Gemini look things up on Google for current events.
        config.tools = [types.Tool(google_search=types.GoogleSearch())]

    response = client.models.generate_content(
        model=CHAT_MODEL,
        contents=[types.Part.from_bytes(data=wav_bytes, mime_type="audio/wav")],
        config=config,
    )
    return (response.text or "").strip() or "Huh, I've got nothing. Try again?"


def warm_up() -> None:
    """Load the voice ahead of time so the first answer isn't extra slow."""
    if TTS_ENGINE == "piper":
        try:
            _load_piper()
        except Exception as error:
            print(f"(Couldn't load Piper voice: {error})")


def speak(text: str, out_path: str) -> None:
    """Write Chad's spoken reply to a WAV file, with the voice effect applied."""
    raw_path = out_path + ".raw.wav"
    _make_voice(text, raw_path)
    _apply_effect(raw_path, out_path)


def _make_voice(text: str, out_path: str) -> None:
    global TTS_MODELS
    if TTS_ENGINE == "piper":
        try:
            _speak_piper(text, out_path)
            return
        except Exception as error:
            print(f"(Piper voice failed: {error})")
    elif TTS_ENGINE == "gemini":
        for model in list(TTS_MODELS):
            try:
                _speak_gemini(model, text, out_path)
                TTS_MODELS = [model]  # remember the one that worked
                return
            except Exception as error:  # e.g. quota hit or model renamed
                print(f"(Gemini voice {model} failed: {error})")
                if "not found" in str(error).lower() and len(TTS_MODELS) > 1:
                    TTS_MODELS.remove(model)  # don't try a missing model again
    if TTS_ENGINE != "espeak":
        print("(Using espeak instead.)")
    _speak_espeak(text, out_path)


def _apply_effect(in_path: str, out_path: str) -> None:
    effect = EFFECT_PRESETS.get(VOICE_EFFECT, VOICE_EFFECT)
    if effect:
        # "gain -n -1" evens out the volume after the effects (stops clipping).
        try:
            result = subprocess.run(
                ["sox", in_path, out_path, *effect.split(), "gain", "-n", "-1"],
                capture_output=True, text=True,
            )
            if result.returncode == 0:
                return
            problem = result.stderr.strip()
        except FileNotFoundError:
            problem = "sox isn't installed (sudo apt install sox)"
        print(f"(Voice effect skipped: {problem})")
    os.replace(in_path, out_path)


_piper_voice = None


def _load_piper():
    global _piper_voice
    if _piper_voice is None:
        from piper import PiperVoice  # imported here so other engines don't need it

        model = VOICES_DIR / f"{PIPER_VOICE}.onnx"
        if not model.exists():
            print(f"Downloading Piper voice {PIPER_VOICE} (one time only)...")
            subprocess.run(
                [sys.executable, "-m", "piper.download_voices", PIPER_VOICE,
                 "--data-dir", str(VOICES_DIR)],
                check=True,
            )
        _piper_voice = PiperVoice.load(str(model))
    return _piper_voice


def _speak_piper(text: str, out_path: str) -> None:
    from piper import SynthesisConfig

    voice = _load_piper()
    with wave.open(out_path, "wb") as f:
        voice.synthesize_wav(text, f, syn_config=SynthesisConfig(length_scale=SPEED))


def _speak_gemini(model: str, text: str, out_path: str) -> None:
    # Gemini's newer voice models use Google's "Interactions" API.
    interaction = client.interactions.create(
        api_version="v1beta",  # the voice models are only on Google's beta API
        model=model,
        input=[{
            "type": "user_input",
            "content": [{
                "type": "text",
                "text": text,
                "annotations": [{"type": "speech_metadata", "style": VOICE_STYLE}],
            }],
        }],
        response_format={"type": "audio"},
        generation_config={"speech_config": [{"voice": VOICE}]},
    )
    audio = interaction.output_audio.data
    if isinstance(audio, str):  # the audio arrives as base64 text
        audio = base64.b64decode(audio)
    if audio[:4] == b"RIFF":  # already a complete WAV file
        with open(out_path, "wb") as f:
            f.write(audio)
        return
    # Otherwise it's raw audio samples: 24 kHz, 16-bit, mono. Add a WAV header.
    with wave.open(out_path, "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(24000)
        f.writeframes(audio)


def _speak_espeak(text: str, out_path: str) -> None:
    # Free, offline, robotic voice. Install with: sudo apt install espeak-ng
    subprocess.run(["espeak-ng", "-s", "160", "-w", out_path, text], check=True)
