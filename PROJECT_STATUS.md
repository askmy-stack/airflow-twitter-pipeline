# Project Status - Social Signal Pipeline

## Current State

This repository is a Twitter/X intelligence pipeline that can ingest real tweet records from fixture files, Xquik exports, or the Twitter/X API. It normalizes tweet provenance, enriches each tweet, and exports both CSV and canonical JSON/JSONL artifacts.

The main pipeline currently supports:

- fixture JSONL demos with explicit sample provenance
- Xquik JSON, JSONL, and CSV exports
- Twitter/X API fallback ingestion
- deterministic local enrichment with no paid API keys
- model-agnostic AI provider selection through environment variables
- strict schema validation for AI enrichment output
- JSONL and grouped JSON export artifacts
- Airflow orchestration
- Streamlit dashboard support
- GitHub Actions CI

## Model-Agnostic AI Enrichment

The enrichment layer is provider-neutral. The default provider is `local`, which keeps the project runnable in CI and on a new laptop without credentials.

Supported provider names:

- `local`
- `openai`
- `anthropic`
- `ollama`
- `huggingface`
- `vllm`
- `lmstudio`
- `together`
- `groq`
- `fireworks`
- `openai_compatible`

Configuration:

```bash
AI_PROVIDER=local
AI_ENRICHMENT_MODE=local
AI_MODEL=local-rule-enricher-v1
AI_API_KEY=
AI_BASE_URL=
```

OpenAI-compatible local model servers such as Ollama, vLLM, and LM Studio can be used by setting `AI_PROVIDER`, `AI_MODEL`, and `AI_BASE_URL`. Hosted providers can use `AI_API_KEY` and, when needed, `AI_BASE_URL`.

Supported enrichment modes are `local`, `api`, `local_llm`, and `hybrid`.

All model responses are treated as untrusted until they pass schema validation. Invalid JSON, missing fields, invalid enum values, or unconfigured providers fall back to local deterministic enrichment.

## Current Quality Gates

Run these before pushing changes:

```bash
python3 -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py
PYTHONPATH=. pytest tests/ -q
FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl \
OUTPUT_CSV_PATH=outputs/refined_tweets.csv \
OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl \
OUTPUT_JSON_PATH=outputs/enriched_tweets.json \
python3 -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Next Recommended Enhancements

- Split `twitter_etl.py` into focused ingestion, enrichment, schema, and export modules.
- Flatten key enrichment fields into CSV for dashboard analytics.
- Update `dashboard.py` to prefer enriched JSON/JSONL over CSV.
- Modernize the Airflow DAG to Airflow 2 style imports.
- Add contributor issues for new connectors and provider adapters.
- Add optional semantic search with embeddings and a local vector index.
