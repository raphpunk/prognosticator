#!/usr/bin/env python3
"""Integration tests covering ingestion, deduplication, storage, and backtesting."""
import sys
import sqlite3
from pathlib import Path
import tempfile
import json

# add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from forecasting.ingest import synthetic_events_expanded, fetch_multiple_feeds
from forecasting.extract import extract_from_article
from forecasting.storage import init_db, insert_articles, insert_extracted, backfill_ingest_log
from forecasting.features import build_daily_aggregates, make_lag_features
from forecasting.model import backtest
from forecasting.security import validate_url, sanitize_domain, SimpleRateLimiter
from forecasting.optimize import create_db_indexes, optimize_db


def test_synthetic_data():
    """Test synthetic data generation."""
    print("Testing synthetic data generation...")
    articles = synthetic_events_expanded(days=10)
    assert len(articles) > 0, "No synthetic articles generated"
    assert all("id" in a for a in articles), "Missing id in articles"
    print("✓ Synthetic data generation works")


def test_extraction():
    """Test extraction pipeline."""
    print("Testing extraction...")
    article = {"id": "test1", "title": "Test News", "text": "Government announced policy", "published": "2025-11-24"}
    extracted = extract_from_article(article, use_spacy=False, classify_content=True)
    assert extracted["id"] == "test1", "ID mismatch"
    assert "content_type" in extracted, "Missing content_type"
    assert "entities" in extracted, "Missing entities"
    print("✓ Extraction works")


def test_storage_and_dedup():
    """Test storage, deduplication, and backfill."""
    print("Testing storage and deduplication...")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(str(db_path))
        
        # insert articles
        articles = [
            {"id": "a1", "title": "Article One", "text": "Content 1", "published": "2025-11-24", "source_url": "test.com"},
            {"id": "a2", "title": "Article One", "text": "Content 1", "published": "2025-11-24", "source_url": "test.com"},  # duplicate
        ]
        insert_articles(str(db_path), articles)
        
        # check storage
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        count = cur.fetchone()[0]
        conn.close()
        assert count == 1, f"Expected 1 unique article, got {count}"
        print("✓ Deduplication works")
        
        # test backfill
        backfill_ingest_log(str(db_path))
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM ingest_log")
        log_count = cur.fetchone()[0]
        conn.close()
        assert log_count > 0, "Backfill failed to populate ingest_log"
        print("✓ Backfill works")


def test_features():
    """Test feature generation."""
    print("Testing feature generation...")
    articles = synthetic_events_expanded(days=15)
    df = build_daily_aggregates(articles)
    assert not df.empty, "Empty feature dataframe"
    assert "article_count" in df.columns, "Missing article_count"
    
    df_lag = make_lag_features(df)
    assert not df_lag.empty, "Empty lag features"
    assert "article_count_lag_1" in df_lag.columns, "Missing lag features"
    print("✓ Feature generation works")


def test_backtesting():
    """Test model backtesting."""
    print("Testing backtesting...")
    articles = synthetic_events_expanded(days=60)
    df = build_daily_aggregates(articles)
    df_lag = make_lag_features(df)
    metrics, preds = backtest(df_lag)
    assert "accuracy" in metrics, "Missing accuracy metric"
    assert metrics["accuracy"] is not None, "Accuracy is None"
    print(f"✓ Backtesting works (accuracy: {metrics['accuracy']:.3f})")


def test_security():
    """Test security utilities."""
    print("Testing security utilities...")
    assert validate_url("https://example.com/feed"), "Valid URL rejected"
    assert not validate_url("ftp://example.com"), "Invalid protocol accepted"
    assert not validate_url("not-a-url"), "Malformed URL accepted"
    print("✓ URL validation works")
    
    assert sanitize_domain("EXAMPLE.COM") == "example.com", "Domain sanitization failed"
    result = sanitize_domain("ex@mple.com")
    assert "@" not in result, "Injection not blocked"
    print("✓ Domain sanitization works")
    
    limiter = SimpleRateLimiter(max_requests=2, window_sec=10)
    assert limiter.is_allowed("test1"), "Rate limiter blocked first request"
    assert limiter.is_allowed("test1"), "Rate limiter blocked second request"
    assert not limiter.is_allowed("test1"), "Rate limiter did not block third request"
    print("✓ Rate limiting works")


def test_optimization():
    """Test optimization utilities."""
    print("Testing optimization utilities...")
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        init_db(str(db_path))
        create_db_indexes(str(db_path))
        optimize_db(str(db_path))
        # verify DB still works
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM articles")
        cur.fetchone()
        conn.close()
        print("✓ Optimization works")


def main():
    print("=" * 60)
    print("INTEGRATION TEST SUITE")
    print("=" * 60)
    
    test_synthetic_data()
    test_extraction()
    test_storage_and_dedup()
    test_features()
    test_backtesting()
    test_security()
    test_optimization()
    
    print("=" * 60)
    print("✓ ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
