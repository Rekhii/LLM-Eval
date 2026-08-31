import os
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

PROMPT = "Reply with exactly one word: pong"


def call_gemini(prompt):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-3.5-flash-lite:generateContent"
    )
    r = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()


def call_groq(prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={
            "model": "openai/gpt-oss-20b",
            "messages": [{"role": "user", "content": prompt}],
        },
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"].strip()


for name, fn, key in [
    ("gemini", call_gemini, GEMINI_KEY),
    ("groq", call_groq, GROQ_KEY),
]:
    if not key:
        print(f"{name:8} NO KEY FOUND in .env")
        continue
    try:
        print(f"{name:8} OK   {fn(PROMPT)!r}")
    except requests.HTTPError as e:
        print(f"{name:8} HTTP {e.response.status_code}  {e.response.text[:200]}")
    except Exception as e:
        print(f"{name:8} FAIL {type(e).__name__}: {e}")