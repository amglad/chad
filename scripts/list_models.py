"""List the Gemini models your API key can use (handy when Google renames them).

Run from the repo folder with the venv on:  python scripts/list_models.py
"""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

for model in client.models.list():
    name = model.name.removeprefix("models/")
    if "flash" in name or "tts" in name:
        print(name)
