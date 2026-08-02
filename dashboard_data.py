"""Data loading helpers for the Streamlit dashboard."""
from __future__ import annotations

import json
import os

import pandas as pd


def load_data(jsonl_path: str, csv_path: str) -> pd.DataFrame:
    if os.path.exists(jsonl_path):
        records = []
        with open(jsonl_path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(_flatten_enriched_record(json.loads(line)))
        return pd.DataFrame(records)
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    df = pd.read_csv(csv_path)
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


def _flatten_enriched_record(record: dict) -> dict:
    tweet = record["tweet"]
    ai = record["ai_enrichment"]
    domain = record["domain_analysis"]
    quality = record["quality"]
    signal = ai["market_or_social_signal"]
    return {
        "user": tweet["author_handle"],
        "text": tweet["text"],
        "favorite_count": tweet["metrics"]["likes"],
        "retweet_count": tweet["metrics"]["retweets"],
        "created_at": pd.to_datetime(tweet["created_at"], errors="coerce"),
        "sentiment": ai["sentiment"],
        "topics": ai["topics"],
        "summary": ai["summary"],
        "intent": ai["intent"],
        "signal_type": signal["signal_type"],
        "primary_domain": domain["primary_domain"],
        "source_confidence": tweet["source_confidence"],
        "requires_human_review": quality["requires_human_review"],
    }
