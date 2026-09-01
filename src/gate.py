import json
import sys

from src.score import FIELDS, matches

THRESHOLD = 0.99
BASELINE_MODEL = "gemini-3.5-flash-lite"


def main():
    tasks = {t["id"]: t["expected"] for t in json.load(open("data/tasks.json", encoding="utf-8"))}
    data = json.load(open("results/latest.json", encoding="utf-8"))

    correct = total = 0
    for run in data["runs"]:
        if run["model"] != BASELINE_MODEL:
            continue
        expected = tasks[run["id"]]
        predicted = run["predicted"] or {}
        for f in FIELDS:
            total += 1
            if matches(f, expected[f], predicted.get(f)):
                correct += 1

    score = correct / total if total else 0
    print(f"{BASELINE_MODEL}: {score:.1%} ({correct}/{total}), threshold {THRESHOLD:.0%}")

    if score < THRESHOLD:
        print("FAIL: accuracy below threshold")
        sys.exit(1)
    print("PASS")


if __name__ == "__main__":
    main()