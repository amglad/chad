"""List the Gemini models your API key can use (handy when Google renames them).

Run from the repo folder with the venv on:  python scripts/list_models.py
"""

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()
for api_version in ["v1", "v1beta"]:
    print(f"--- {api_version} ---")
    beta = genai.Client(
        api_key=os.environ["GEMINI_API_KEY"],
        http_options={"api_version": api_version},
    )
    for model in beta.models.list():
        print(model.name.removeprefix("models/"))
