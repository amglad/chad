"""Everything that talks to the cloud AI lives here, so swapping providers
later only means changing this file.

think(wav_bytes) -> reply text     (hears the question and answers it)
speak(text, out_path)              (turns the reply into a WAV file)
"""

import base64
import os
import subprocess
import wave

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
TTS_ENGINE = os.getenv("TTS_ENGINE", "gemini")  # "gemini" or "espeak"
VOICE = os.getenv("VOICE", "Puck")  # Gemini voice name
VOICE_STYLE = os.getenv("VOICE_STYLE", "upbeat, energetic and friendly")
USE_SEARCH = os.getenv("USE_SEARCH", "true").lower() == "true"

PERSONALITY = os.getenv(
    "PERSONALITY",
    "You are Chad, a small, upbeat action figure who talks with people out loud. "
    "The user's message is a voice recording. Answer what they said in one to "
    "three short, casual sentences, because your reply will be spoken aloud. "
    "No lists, markdown, emoji, or URLs. If you couldn't make out the audio, "
    "say so playfully and ask them to try again.",
)

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
        system_instruction=PERSONALITY,
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


def speak(text: str, out_path: str) -> None:
    """Write Chad's spoken reply to a WAV file. Falls back to espeak on errors."""
    global TTS_MODELS
    if TTS_ENGINE == "gemini":
        for model in list(TTS_MODELS):
            try:
                _speak_gemini(model, text, out_path)
                TTS_MODELS = [model]  # remember the one that worked
                return
            except Exception as error:  # e.g. quota hit or model renamed
                print(f"(Gemini voice {model} failed: {error})")
                if "not found" in str(error).lower() and len(TTS_MODELS) > 1:
                    TTS_MODELS.remove(model)  # don't try a missing model again
        print("(Using espeak instead.)")
    _speak_espeak(text, out_path)


def _speak_gemini(model: str, text: str, out_path: str) -> None:
    # Gemini's newer voice models use Google's "Interactions" API.
    interaction = client.interactions.create(
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
