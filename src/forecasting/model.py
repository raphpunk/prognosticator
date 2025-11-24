"""Simple modeling and backtesting utilities.

Uses scikit-learn RandomForestClassifier for a demo task: predict whether next-day article_count increases.
The functions are written to run with minimal deps in demo mode.
"""
from typing import Tuple
import pandas as pd


def make_labels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["next_count"] = df["article_count"].shift(-1)
    df = df.dropna()
    df["label_up"] = (df["next_count"] > df["article_count"]).astype(int)
    return df


def train_demo_model(X: pd.DataFrame, y: pd.Series):
    try:
        from sklearn.ensemble import RandomForestClassifier
    except Exception as e:
        raise RuntimeError("scikit-learn is required to train model. Install requirements.txt") from e

    clf = RandomForestClassifier(n_estimators=50, random_state=0)
    clf.fit(X, y)
    return clf


def backtest(df: pd.DataFrame) -> Tuple[dict, pd.DataFrame]:
    from sklearn.metrics import accuracy_score, precision_score, recall_score

    df = make_labels(df)
    feature_cols = [c for c in df.columns if c.startswith("article_count_lag_")]
    results = []
    # simple expanding-window backtest
    for i in range(10, len(df) - 1):
        train = df.iloc[:i]
        test = df.iloc[i : i + 1]
        clf = train_demo_model(train[feature_cols], train["label_up"])  # may raise
        pred = clf.predict(test[feature_cols])[0]
        results.append({"date": test.index[0], "y_true": int(test["label_up"].values[0]), "y_pred": int(pred)})
    res_df = pd.DataFrame(results).set_index("date")
    if res_df.empty:
        metrics = {"accuracy": None, "precision": None, "recall": None}
    else:
        metrics = {
            "accuracy": float(accuracy_score(res_df["y_true"], res_df["y_pred"])),
            "precision": float(precision_score(res_df["y_true"], res_df["y_pred"])),
            "recall": float(recall_score(res_df["y_true"], res_df["y_pred"])),
        }
    return metrics, res_df


if __name__ == "__main__":
    from forecasting.features import build_daily_aggregates, make_lag_features
    from forecasting.ingest import synthetic_events_expanded

    arts = synthetic_events_expanded(60)
    df = build_daily_aggregates(arts)
    df2 = make_lag_features(df)
    print(df2.head())
    metrics, history = backtest(df2)
    print(metrics)
