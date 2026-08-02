import json

import pandas as pd

from dashboard_data import load_data


def test_load_data_reads_csv_with_pandas(tmp_path):
    csv_path = tmp_path / "refined.csv"
    csv_path.write_text(
        "user,text,favorite_count,retweet_count,created_at\n"
        "alice,hello world,10,2,2024-01-01T12:00:00\n"
    )

    df = load_data(str(tmp_path / "missing.jsonl"), str(csv_path))

    assert len(df) == 1
    assert df.iloc[0]["user"] == "alice"
    assert pd.api.types.is_datetime64_any_dtype(df["created_at"])


def test_load_data_handles_path_with_sql_metacharacters(tmp_path):
    csv_path = tmp_path / "data' OR 1=1 --.csv"
    csv_path.write_text(
        "user,text,favorite_count,retweet_count,created_at\n"
        "bob,safe read,5,1,2024-02-01T08:00:00\n"
    )

    df = load_data(str(tmp_path / "missing.jsonl"), str(csv_path))

    assert len(df) == 1
    assert df.iloc[0]["user"] == "bob"


def test_load_data_prefers_jsonl_over_csv(tmp_path):
    jsonl_path = tmp_path / "enriched.jsonl"
    jsonl_path.write_text(
        json.dumps(
            {
                "tweet": {
                    "author_handle": "carol",
                    "text": "from jsonl",
                    "metrics": {"likes": 3, "retweets": 1},
                    "created_at": "2024-03-01T10:00:00",
                    "source_confidence": 0.9,
                },
                "ai_enrichment": {
                    "sentiment": "positive",
                    "topics": ["ai"],
                    "summary": "summary",
                    "intent": "inform",
                    "market_or_social_signal": {"signal_type": "news"},
                },
                "domain_analysis": {"primary_domain": "tech"},
                "quality": {"requires_human_review": False},
            }
        )
        + "\n"
    )
    csv_path = tmp_path / "refined.csv"
    csv_path.write_text(
        "user,text,favorite_count,retweet_count,created_at\n"
        "ignored,csv row,1,0,2024-01-01T12:00:00\n"
    )

    df = load_data(str(jsonl_path), str(csv_path))

    assert len(df) == 1
    assert df.iloc[0]["user"] == "carol"


def test_load_data_returns_empty_when_no_sources(tmp_path):
    df = load_data(
        str(tmp_path / "missing.jsonl"),
        str(tmp_path / "missing.csv"),
    )
    assert df.empty
