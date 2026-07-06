import json

import pytest

from twitter_etl import (
    BaseEnrichmentProvider,
    _normalize_tweet,
    _normalise_tweets,
    _provider_from_env,
    enrich_tweet,
    load_xquik_rows,
    run_twitter_etl,
    validate_enriched_record,
)


@pytest.fixture(autouse=True)
def clear_ai_provider_env(monkeypatch):
    for name in (
        "AI_PROVIDER",
        "AI_ENRICHMENT_MODE",
        "AI_MODEL",
        "AI_API_KEY",
        "AI_BASE_URL",
        "OPENAI_API_KEY",
        "OPENAI_MODEL",
        "ANTHROPIC_API_KEY",
    ):
        monkeypatch.delenv(name, raising=False)


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


def test_xquik_rows_normalise_to_legacy_csv_projection(tmp_path):
    export_path = tmp_path / "xquik.jsonl"
    export_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "id": "1",
                        "fullText": "First Xquik row",
                        "author": {"username": "alice"},
                        "like_count": 4,
                        "createdAt": "2026-07-06T12:00:00Z",
                    }
                ),
                json.dumps(
                    {
                        "id": "2",
                        "text": "Second row",
                        "username": "bob",
                        "createdAt": "2026-07-06T12:01:00Z",
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )

    rows = _normalise_tweets(load_xquik_rows(export_path))

    assert rows == [
        {
            "user": "alice",
            "text": "First Xquik row",
            "favorite_count": 4,
            "retweet_count": 0,
            "created_at": "2026-07-06T12:00:00Z",
        },
        {
            "user": "bob",
            "text": "Second row",
            "favorite_count": 0,
            "retweet_count": 0,
            "created_at": "2026-07-06T12:01:00Z",
        },
    ]


def test_normalise_tweets_skips_empty_text():
    rows = _normalise_tweets([{"text": ""}, {"text": "keep me"}])

    assert len(rows) == 1
    assert rows[0]["text"] == "keep me"


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
    assert record["quality"]["ai_provider"] == "local"
    assert record["quality"]["ai_model"] == "local-rule-enricher-v1"
    assert record["quality"]["enrichment_mode"] == "local"
    assert record["quality"]["fallback_used"] is False
    assert record["quality"]["validated"] is True
    assert record["quality"]["validation_errors"] == []


def test_provider_selection_defaults_to_local(monkeypatch):
    monkeypatch.delenv("AI_PROVIDER", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    provider = _provider_from_env()

    assert provider.provider_name == "local"
    assert provider.model == "local-rule-enricher-v1"
    assert provider.enrichment_mode == "local"


def test_openai_provider_without_credentials_falls_back_to_local(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "openai")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "provider-1",
            "text": "OpenAI released an AI infrastructure update.",
            "username": "ai_lab",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    record = enrich_tweet(row)

    assert record["quality"]["ai_provider"] == "local"
    assert record["quality"]["fallback_used"] is True
    assert record["quality"]["validated"] is True


def test_openai_compatible_mock_provider_can_return_valid_json(monkeypatch):
    class MockProvider(BaseEnrichmentProvider):
        provider_name = "openai_compatible"
        default_model = "mock-model"

        @property
        def enrichment_mode(self):
            return "api"

        def enrich(self, row):
            return {
                "sentiment": "positive",
                "topics": ["ai_ml", "infrastructure"],
                "entities": [{"name": "OpenAI", "type": "company", "confidence": 0.9}],
                "summary": "OpenAI released a new infrastructure update.",
                "toxicity_risk": {"level": "none", "score": 0.0, "reason": "No toxicity indicators detected."},
                "intent": "product_update",
                "market_or_social_signal": {
                    "signal_type": "adoption",
                    "strength": "medium",
                    "rationale": "The tweet references adoption or deployment.",
                },
            }

    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_MODEL", "mock-model")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setitem(__import__("twitter_etl").PROVIDER_REGISTRY, "openai_compatible", MockProvider)
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "provider-2",
            "text": "OpenAI deployment adoption improves AI infrastructure.",
            "username": "ai_lab",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    record = enrich_tweet(row)

    assert record["ai_enrichment"]["summary"] == "OpenAI released a new infrastructure update."
    assert record["quality"]["ai_provider"] == "openai_compatible"
    assert record["quality"]["ai_model"] == "mock-model"
    assert record["quality"]["enrichment_mode"] == "api"
    assert record["quality"]["fallback_used"] is False
    assert record["quality"]["validated"] is True


def test_invalid_provider_json_falls_back_to_local(monkeypatch):
    class InvalidProvider(BaseEnrichmentProvider):
        provider_name = "openai_compatible"
        default_model = "broken-model"

        @property
        def enrichment_mode(self):
            return "api"

        def enrich(self, row):
            return {
                "sentiment": "excited",
                "topics": ["ai_ml"],
                "entities": [],
                "summary": "Invalid enum payload.",
                "toxicity_risk": {"level": "none", "score": 0.0, "reason": "No toxicity indicators detected."},
                "intent": "product_update",
                "market_or_social_signal": {
                    "signal_type": "none",
                    "strength": "low",
                    "rationale": "No grounded market or social signal detected.",
                },
            }

    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setitem(__import__("twitter_etl").PROVIDER_REGISTRY, "openai_compatible", InvalidProvider)
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "provider-3",
            "text": "AI infrastructure update released.",
            "username": "ai_lab",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    record = enrich_tweet(row)

    assert record["quality"]["ai_provider"] == "local"
    assert record["quality"]["fallback_used"] is True
    assert record["ai_enrichment"]["sentiment"] in {"positive", "neutral", "mixed", "negative"}
    assert record["quality"]["validated"] is True


def test_hybrid_mode_records_valid_model_enrichment(monkeypatch):
    class HybridProvider(BaseEnrichmentProvider):
        provider_name = "openai_compatible"
        default_model = "hybrid-model"

        @property
        def enrichment_mode(self):
            return "api"

        def enrich(self, row):
            return {
                "sentiment": "mixed",
                "topics": ["ai_ml", "finance"],
                "entities": [{"name": "NVIDIA", "type": "company", "confidence": 0.92}],
                "summary": "NVIDIA AI infrastructure demand is affecting market expectations.",
                "toxicity_risk": {"level": "none", "score": 0.0, "reason": "No toxicity indicators detected."},
                "intent": "market_commentary",
                "market_or_social_signal": {
                    "signal_type": "bullish",
                    "strength": "medium",
                    "rationale": "The tweet includes positive market language.",
                },
            }

    monkeypatch.setenv("AI_PROVIDER", "openai_compatible")
    monkeypatch.setenv("AI_ENRICHMENT_MODE", "hybrid")
    monkeypatch.setenv("AI_API_KEY", "test-key")
    monkeypatch.setitem(__import__("twitter_etl").PROVIDER_REGISTRY, "openai_compatible", HybridProvider)
    row = _normalize_tweet(
        {
            "_source_connector": "twitter_api",
            "id": "provider-4",
            "text": "NVIDIA AI infrastructure demand looks bullish for market expectations.",
            "username": "market_ai",
            "created_at": "2026-07-06T12:00:00Z",
        }
    )

    record = enrich_tweet(row)

    assert record["ai_enrichment"]["sentiment"] == "mixed"
    assert record["quality"]["ai_provider"] == "openai_compatible"
    assert record["quality"]["enrichment_mode"] == "hybrid"
    assert record["quality"]["fallback_used"] is False
    assert record["quality"]["validated"] is True


def test_ollama_provider_uses_local_llm_mode_without_api_key(monkeypatch):
    monkeypatch.setenv("AI_PROVIDER", "ollama")
    monkeypatch.delenv("AI_API_KEY", raising=False)
    monkeypatch.setenv("AI_BASE_URL", "http://localhost:11434/v1")
    monkeypatch.setenv("AI_MODEL", "llama3.1")

    provider = _provider_from_env()

    assert provider.provider_name == "ollama"
    assert provider.model == "llama3.1"
    assert provider.enrichment_mode == "local_llm"
    assert provider.is_configured() is True


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
