import json

import pandas as pd
import streamlit as st

from src.score import FIELDS, matches

st.set_page_config(page_title="LLM-Eval", layout="wide")

tasks = {t["id"]: t for t in json.load(open("data/tasks.json", encoding="utf-8"))}
data = json.load(open("results/latest.json", encoding="utf-8"))
models = data["models"]

rows = []
for run in data["runs"]:
    expected = tasks[run["id"]]["expected"]
    predicted = run["predicted"] or {}
    for f in FIELDS:
        rows.append({
            "model": run["model"],
            "id": run["id"],
            "field": f,
            "expected": expected[f],
            "predicted": predicted.get(f),
            "correct": matches(f, expected[f], predicted.get(f)),
        })

df = pd.DataFrame(rows)

st.title("LLM-Eval")
st.caption(f"40 hand-labeled job postings, 8 fields, 3 models. Last run {data['timestamp'][:16]}")

overall = df.groupby("model")["correct"].mean().reindex(models)
cols = st.columns(len(models))
for col, model in zip(cols, models):
    col.metric(model.split("/")[-1], f"{overall[model]:.0%}")

st.subheader("Accuracy by field")
pivot = df.pivot_table(index="field", columns="model", values="correct", aggfunc="mean")
pivot = pivot.reindex(FIELDS)[models]
st.dataframe(pivot.style.format("{:.0%}"), use_container_width=True)
st.bar_chart(pivot)

st.subheader("Inferred 'onsite' where the posting said nothing")
inferred = {
    m: sum(
        1 for r in data["runs"]
        if r["model"] == m
        and tasks[r["id"]]["expected"]["remote"] == "unclear"
        and (r["predicted"] or {}).get("remote") == "onsite"
    )
    for m in models
}
st.bar_chart(pd.Series(inferred).reindex(models))
st.caption(
    "Postings that state no work arrangement. A model answering 'onsite' is "
    "inventing information rather than reporting its absence."
)

st.subheader("Failures")
model_pick = st.selectbox("Model", models)
misses = df[(df["model"] == model_pick) & (~df["correct"])]
st.dataframe(misses[["id", "field", "expected", "predicted"]], use_container_width=True)