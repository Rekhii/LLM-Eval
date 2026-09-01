import json
from collections import defaultdict

FIELDS = [
    "title",
    "company",
    "location",
    "years_experience",
    "employment_type",
    "education_required",
    "remote",
    "salary_min",
]

ALIASES = {
    "bangalore": "bengaluru",
    "bombay": "mumbai",
    "calcutta": "kolkata",
    "madras": "chennai",
    "gurgaon": "gurugram",
    "new delhi": "delhi",
    "delhi ncr": "delhi",
    "delhi / ncr": "delhi",
    "delhi/ncr": "delhi",
    "mumbai (all areas)": "mumbai",
}

REMOTE_VALUES = {"remote", "hybrid", "onsite", "unclear"}


def norm_city(c):
    c = str(c).strip().lower()
    return ALIASES.get(c, c)


def norm_text(v):
    if v is None:
        return None
    s = str(v).strip()
    if s.lower().startswith("ug: "):
        s = s[4:]
    return s.strip().lower()


def matches(field, expected, predicted):
    if field == "location":
        if expected is None or predicted is None:
            return expected == predicted
        if not isinstance(predicted, list):
            predicted = [predicted]
        return {norm_city(c) for c in expected} == {norm_city(c) for c in predicted}
    if field in ("years_experience", "salary_min"):
        if expected is None or predicted is None:
            return expected == predicted
        try:
            return float(expected) == float(predicted)
        except (TypeError, ValueError):
            return False
    return norm_text(expected) == norm_text(predicted)


def main():
    tasks = {t["id"]: t["expected"] for t in json.load(open("data/tasks.json", encoding="utf-8"))}
    data = json.load(open("results/latest.json", encoding="utf-8"))

    correct = defaultdict(lambda: defaultdict(int))
    total = defaultdict(lambda: defaultdict(int))
    violations = defaultdict(int)
    parse_fail = defaultdict(int)
    hallucinated_salary = defaultdict(int)
    inferred_onsite = defaultdict(int)
    misses = []

    for run in data["runs"]:
        model, expected = run["model"], tasks[run["id"]]
        predicted = run["predicted"]

        if predicted is None:
            parse_fail[model] += 1
            for f in FIELDS:
                total[model][f] += 1
            continue

        got_remote = predicted.get("remote")
        if got_remote is None or norm_text(got_remote) not in REMOTE_VALUES:
            violations[model] += 1

        if expected["remote"] == "unclear" and norm_text(got_remote) == "onsite":
            inferred_onsite[model] += 1

        if expected["salary_min"] is None and predicted.get("salary_min") is not None:
            hallucinated_salary[model] += 1

        for f in FIELDS:
            total[model][f] += 1
            if matches(f, expected[f], predicted.get(f)):
                correct[model][f] += 1
            else:
                misses.append((model, run["id"], f, expected[f], predicted.get(f)))

    models = data["models"]
    width = max(len(m) for m in models) + 2

    print("\nField accuracy\n")
    print(" " * 22 + "".join(f"{m:>{width}}" for m in models))
    for f in FIELDS:
        row = "".join(
            f"{correct[m][f] / total[m][f]:>{width}.0%}" if total[m][f] else f"{'-':>{width}}"
            for m in models
        )
        print(f"{f:<22}{row}")

    print("\n" + "-" * (22 + width * len(models)))
    overall = "".join(
        f"{sum(correct[m].values()) / sum(total[m].values()):>{width}.0%}" for m in models
    )
    print(f"{'OVERALL':<22}{overall}")

    print("\nOther metrics\n")
    for label, counter in [
        ("parse failures", parse_fail),
        ("schema violations", violations),
        ("hallucinated salary", hallucinated_salary),
        ("inferred onsite", inferred_onsite),
    ]:
        row = "".join(f"{counter[m]:>{width}}" for m in models)
        print(f"{label:<22}{row}")

    print(f"\nMisses ({len(misses)})\n")
    for model, task_id, field, exp, got in misses:
        print(f"  {model:<24} #{task_id:<3} {field:<20} expected {exp!r}  got {got!r}")


if __name__ == "__main__":
    main()