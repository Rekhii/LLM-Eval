import json
import os
import time
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

MODELS = {
    "gemini-3.5-flash-lite": "gemini",
    "openai/gpt-oss-20b": "groq",
    "openai/gpt-oss-120b": "groq",
}

PROMPT = """Extract these fields from the job posting below. Return ONLY a JSON object, no explanation, no markdown fences.

Fields:
- title: the job title from the header, as a string
- company: the company name, as a string
- location: cities, as a list of strings
- years_experience: minimum years required, as a number
- employment_type: e.g. "Full Time, Permanent", as a string
- education_required: e.g. "Any Graduate", as a string
- remote: one of "remote", "hybrid", "onsite", "unclear"
- salary_min: minimum annual salary in lakhs, as a number. "15-22.5 Lacs P.A." gives 15. "Unpaid" gives 0. "Not Disclosed" gives null.

Use null for any field the posting does not state. Do not guess.

JOB POSTING:
{posting}"""


def call_gemini(model, prompt):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    r = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def call_groq(model, prompt):
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}"},
        json={"model": model, "messages": [{"role": "user", "content": prompt}]},
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def call(model, provider, prompt):
    for attempt in range(4):
        try:
            if provider == "gemini":
                return call_gemini(model, prompt)
            return call_groq(model, prompt)
        except requests.HTTPError as e:
            if e.response.status_code == 429 and attempt < 3:
                wait = 10 * (attempt + 1)
                print(f"      rate limited, waiting {wait}s")
                time.sleep(wait)
                continue
            raise


def parse_json(raw):
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object found")
    return json.loads(text[start : end + 1])


def main():
    tasks = json.load(open("data/tasks.json", encoding="utf-8"))
    runs = []

    for model, provider in MODELS.items():
        print(f"\n{model}")
        for task in tasks:
            posting = open(
                f"data/postings/{task['file']}", encoding="utf-8"
            ).read()
            prompt = PROMPT.format(posting=posting)

            record = {"model": model, "id": task["id"], "file": task["file"]}
            raw = ""
            try:
                raw = call(model, provider, prompt)
                record["raw"] = raw
                record["predicted"] = parse_json(raw)
                record["error"] = None
                print(f"  {task['id']:3}  ok")
            except Exception as e:
                record["raw"] = raw
                record["predicted"] = None
                record["error"] = f"{type(e).__name__}: {e}"
                print(f"  {task['id']:3}  FAIL  {record['error'][:60]}")

            runs.append(record)
            time.sleep(4)

    out = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "models": list(MODELS),
        "runs": runs,
    }
    os.makedirs("results", exist_ok=True)
    with open("results/latest.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    failed = sum(1 for r in runs if r["error"])
    print(f"\n{len(runs)} runs, {failed} failed, written to results/latest.json")


if __name__ == "__main__":
    main()