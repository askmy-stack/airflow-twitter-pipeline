import json

from twitter_etl import (
    _normalize_tweet,
    enrich_tweet,
    load_xquik_rows,
    run_twitter_etl,
    validate_enriched_record,
)


def test_load_xquik_jsonl_rows(tmp_path):
    export_path = tmp_path / "xquik.jsonl"
    export_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "1",
                        "fullText": "OpenAI released an AI agent infrastructure update",
                        "author": {"username": "alice"},
                        "like_count": 4,
                    }
                ),
                json.dumps({"id": "2", "text": "Second row", "username": "bob"}),
            ]
        ),
        encoding="utf-8",
    )

    rows = load_xquik_rows(export_path)

    assert len(rows) == 2
    assert rows[0]["fullText"] == "OpenAI released an AI agent infrastructure update"


def test_enriched_record_has_required_schema():
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "123",
            "full_text": "NVIDIA GPU adoption is accelerating cloud AI infrastructure.",
            "user": {"screen_name": "technews", "name": "Tech News"},
            "created_at": "2026-07-06T12:00:00Z",
            "favorite_count": 12,
            "retweet_count": 3,
        }
    )

    record = enrich_tweet(row)

    assert record["tweet"]["source_confidence"] == "verified"
    assert record["ai_enrichment"]["sentiment"] in {"positive", "neutral", "mixed"}
    assert record["domain_analysis"]["primary_domain"] in {"ai_ml", "cloud", "semiconductors"}
    assert record["quality"]["validated"] is True
    assert record["quality"]["validation_errors"] == []


def test_missing_xquik_tweet_id_is_exported_not_verified():
    row = _normalize_tweet(
        {
            "_source_connector": "xquik",
            "text": "Airflow pipeline reliability improved after the Kafka deployment.",
            "author": {"username": "infra"},
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    assert row["tweet_id"] == ""
    assert row["source_confidence"] == "exported"

    record = enrich_tweet(row)
    assert record["tweet"]["source_confidence"] == "exported"
    assert record["quality"]["validated"] is True
    assert record["quality"]["requires_human_review"] is True


def test_fixture_sample_cannot_be_verified():
    row = _normalize_tweet(
        {
            "_source_connector": "fixture",
            "_is_sample": True,
            "id": "sample-1",
            "text": "Sample AI research tweet for local demos.",
            "username": "demo",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    assert row["is_sample"] is True
    assert row["source_confidence"] == "sample"

    record = enrich_tweet(row)
    record["tweet"]["source_confidence"] = "verified"
    errors = validate_enriched_record(record)
    assert "sample tweets must use sample source_confidence" in errors


def test_invalid_ai_output_is_rejected():
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "456",
            "text": "A cybersecurity breach created material infrastructure risk.",
            "username": "security",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )
    record = enrich_tweet(row)
    record["ai_enrichment"]["sentiment"] = "excited"
    record["domain_analysis"]["primary_domain"] = "unsupported"

    errors = validate_enriched_record(record)

    assert "ai_enrichment.sentiment is invalid" in errors
    assert "domain_analysis.primary_domain is invalid" in errors


def test_run_pipeline_writes_csv_json_and_jsonl(tmp_path, monkeypatch):
    fixture = tmp_path / "fixture.jsonl"
    fixture.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "fixture-1",
                        "text": "AI research benchmark shows stronger RAG evaluation results.",
                        "username": "demo_ai",
                        "created_at": "2026-07-06T12:00:00Z",
                        "is_sample": True,
                    }
                ),
                json.dumps(
                    {
                        "id": "fixture-2",
                        "text": "Cloud infrastructure outage warning affects platform reliability.",
                        "username": "demo_cloud",
                        "created_at": "2026-07-06T12:01:00Z",
                        "is_sample": True,
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    csv_path = tmp_path / "refined.csv"
    jsonl_path = tmp_path / "enriched.jsonl"
    json_path = tmp_path / "enriched.json"

    monkeypatch.setenv("FIXTURE_TWEETS_PATH", str(fixture))
    monkeypatch.setenv("OUTPUT_CSV_PATH", str(csv_path))
    monkeypatch.setenv("OUTPUT_JSONL_PATH", str(jsonl_path))
    monkeypatch.setenv("OUTPUT_JSON_PATH", str(json_path))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    result = run_twitter_etl()

    assert result["records"] == 2
    assert csv_path.exists()
    assert jsonl_path.exists()
    assert json_path.exists()
    jsonl_records = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    grouped = json.loads(json_path.read_text(encoding="utf-8"))
    assert len(jsonl_records) == 2
    assert grouped["metadata"]["record_count"] == 2
    assert all(record["tweet"]["is_sample"] for record in jsonl_records)
