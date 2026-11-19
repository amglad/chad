"""Everything that talks to the cloud AI lives here, so swapping providers
later only means changing this file.

think(wav_bytes) -> reply text     (hears the question and answers it)
speak(text, out_path)              (turns the reply into a WAV file)
"""

import os
import subprocess
import wave

from google import genai
from google.genai import types

CHAT_MODEL = os.getenv("CHAT_MODEL", "gemini-3.5-flash-lite")
TTS_MODEL = os.getenv("TTS_MODEL", "gemini-3.8-flash-lite-tts")
# How hard the model "thinks" before answering. Less = faster replies.
# Flash-Lite models accept "minimal"; gemini-3.8-flash needs "low" or higher.
THINKING_LEVEL = os.getenv(
    "THINKING_LEVEL", "minimal" if "lite" in CHAT_MODEL else "low"
)
TTS_ENGINE = os.getenv("TTS_ENGINE", "gemini")  # "gemini" or "espeak"
VOICE = os.getenv("VOICE", "Puck")  # Gemini voice name
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
    if TTS_ENGINE == "gemini":
        try:
            _speak_gemini(text, out_path)
            return
        except Exception as error:  # e.g. quota hit or model renamed
            print(f"(Gemini voice failed: {error}. Using espeak instead.)")
    _speak_espeak(text, out_path)


def _speak_gemini(text: str, out_path: str) -> None:
    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=f"Say in an upbeat, friendly voice: {text}",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=VOICE)
                )
            ),
        ),
    )
    audio = response.candidates[0].content.parts[0].inline_data.data
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
