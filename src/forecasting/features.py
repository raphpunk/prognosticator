"""Feature generation for prototype.

Generates simple day-level aggregates (article counts and unique entity counts) for demo backtests.
"""
import pandas as pd
from typing import List, Dict


def build_daily_aggregates(articles: List[Dict]) -> pd.DataFrame:
    """Given list of article dicts with `published` (ISO date) and optional `entities`,
    return a DataFrame indexed by date with features.
    """
    records = []
    for a in articles:
        date = a.get("published")
        if isinstance(date, str) and "T" in date:
            date = date.split("T")[0]
        records.append({
            "date": date,
            "id": a.get("id"),
            "entities": a.get("entities", []),
            "content_type": a.get("content_type", None),
        })

    df = pd.DataFrame(records)
    if df.empty:
        return pd.DataFrame()
    df["date"] = pd.to_datetime(df["date"]).dt.date
    # compute article counts and per-content-type counts
    grouped = df.groupby("date").agg(
        article_count=("id", "count"),
        unique_entities=("entities", lambda x: len({e["text"] for lst in x for e in lst})),
    )

    # add per-content-type counts from the `content_type` field when available
    types = ["socio", "political", "economic", "health", "tech", "environment", "security", "other"]
    for t in types:
        grouped[f"count_{t}"] = df.groupby("date")["content_type"].apply(lambda arr, tt=t: int((arr == tt).sum()))
    grouped = grouped.sort_index()
    return grouped


def make_lag_features(df: pd.DataFrame, lags: List[int] = [1, 3, 7]) -> pd.DataFrame:
    out = df.copy()
    for l in lags:
        out[f"article_count_lag_{l}"] = out["article_count"].shift(l)
    out = out.dropna()
    return out


if __name__ == "__main__":
    from forecasting.ingest import synthetic_events_expanded
    arts = synthetic_events_expanded(14)
    df = build_daily_aggregates(arts)
    print(df.head())
