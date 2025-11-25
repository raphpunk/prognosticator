#!/usr/bin/env python3
"""Export articles and query-build for feeding into an Ollama model.

Usage:
  # export recent articles to JSONL
  PYTHONPATH=src python scripts/ollama_feed.py --mode export --out data/ollama_context.jsonl --limit 200

  # query mode: find top-5 relevant articles for a question and (optionally) call ollama
  PYTHONPATH=src python scripts/ollama_feed.py --mode query --question "What is driving recent tech layoffs?" --topk 5 --model llama2

The script builds a simple TF-IDF index over article text and ranks relevance.
If `ollama` is installed and `--run-model` is set, the script will try to call
`ollama run <model>` and pipe the constructed prompt to its stdin.
"""
import argparse
import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


def load_cfg_from_feedsjson(path="feeds.json"):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r") as fh:
            data = json.load(fh)
            return data.get("ollama", {})
    except Exception:
        return {}


def load_articles(db_path="data/live.db", limit=500, days=None):
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return []
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    query = "SELECT id, title, text, published, source_url FROM articles"
    params = []
    if days is not None:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        query += " WHERE published >= ?"
        params.append(cutoff)
    query += " ORDER BY published DESC LIMIT ?"
    params.append(limit)
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    articles = []
    for r in rows:
        aid, title, text, published, source_url = r
        articles.append({
            "id": aid,
            "title": title,
            "text": text or "",
            "source_url": source_url,
            "published": published,
        })
    return articles


def export_jsonl(articles, out_path):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        for a in articles:
            fh.write(json.dumps(a, default=str) + "\n")
    print(f"Exported {len(articles)} articles to {out_path}")


def build_tfidf(articles):
    texts = [a["text"] for a in articles]
    vec = TfidfVectorizer(max_features=20000, stop_words="english")
    X = vec.fit_transform(texts)
    return vec, X


def find_topk(vec, X, articles, query, topk=5):
    qv = vec.transform([query])
    sims = linear_kernel(qv, X).flatten()
    idxs = sims.argsort()[::-1][:topk]
    results = [(articles[i], float(sims[i])) for i in idxs]
    return results


PROMPT_TEMPLATE = (
    "You are an analyst assistant. Use the following context snippets from recent news articles to answer the question.\n\n"
    "Context:\n{context}\n\nQuestion: {question}\n\nAnswer concisely, and cite the article indices where relevant."
)


def build_prompt(question, top_articles):
    pieces = []
    for i, (art, score) in enumerate(top_articles, start=1):
        # include title, first 600 chars of text
        text_snip = (art["text"] or "").strip().replace("\n", " ")[:600]
        pieces.append(f"[{i}] {art['title'] or '[no title]'} (score={score:.3f})\n{text_snip}\nSource: {art['source_url']}")
    context = "\n---\n".join(pieces)
    return PROMPT_TEMPLATE.format(context=context, question=question)


def call_ollama(model, prompt):
    import shutil
    # Check for ollama binary
    if not shutil.which("ollama"):
        print("`ollama` CLI not found in PATH. Install Ollama or run the model manually.")
        return None
    # call `ollama run <model>` and pipe prompt to stdin
    proc = subprocess.run(["ollama", "run", model], input=prompt, text=True, capture_output=True)
    if proc.returncode != 0:
        print("Ollama run failed:", proc.stderr)
        return None
    return proc.stdout


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["export", "query"], default="export")
    parser.add_argument("--db", default="data/live.db")
    parser.add_argument("--out", default="data/ollama_context.jsonl")
    parser.add_argument("--limit", type=int, default=500)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--question", type=str, default=None)
    parser.add_argument("--topk", type=int, default=5)
    parser.add_argument("--model", type=str, default="ollama/model:latest")
    parser.add_argument("--run-model", action="store_true", help="If set, attempt to call ollama with the constructed prompt")
    args = parser.parse_args()

    articles = load_articles(args.db, limit=args.limit, days=args.days)
    if not articles:
        print("No articles loaded; exiting")
        sys.exit(1)

    if args.mode == "export":
        export_jsonl(articles, args.out)
        return

    # query mode
    if not args.question:
        print("Provide --question for query mode")
        sys.exit(1)

    vec, X = build_tfidf(articles)
    top = find_topk(vec, X, articles, args.question, topk=args.topk)
    prompt = build_prompt(args.question, top)
    print("--- Prompt (truncated 1000 chars) ---")
    print(prompt[:1000])

    if args.run_model:
        try:
            cfg = load_cfg_from_feedsjson()
            mode = cfg.get("mode", "cli")
            if mode == "cli":
                out = call_ollama(args.model, prompt)
                if out is not None:
                    print("--- Model output ---")
                    print(out)
            else:
                # HTTP mode: POST to host:port/api/predict (best-effort)
                import requests
                host = cfg.get("host", "http://localhost")
                port = cfg.get("port", 11434)
                url = f"{host.rstrip('/') }:{port}/api/predict"
                headers = {"Content-Type": "application/json"}
                if cfg.get("api_key"):
                    headers["Authorization"] = f"Bearer {cfg.get('api_key') }"
                payload = {"model": cfg.get("model", args.model), "prompt": prompt}
                resp = requests.post(url, json=payload, headers=headers, timeout=20)
                if resp.status_code != 200:
                    print("HTTP call failed:", resp.status_code, resp.text)
                else:
                    print("--- Model output ---")
                    try:
                        print(resp.json())
                    except Exception:
                        print(resp.text)
        except Exception as e:
            print("Error calling ollama:", e)


if __name__ == "__main__":
    main()
