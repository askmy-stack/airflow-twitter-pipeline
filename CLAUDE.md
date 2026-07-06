# AI Assistant Guide

This file gives AI coding assistants and maintainers a compact map of the current repository. Keep it synchronized with `README.md` when major behavior changes.

## Project Summary

Social Signal Pipeline ingests real tweet records from fixture JSONL, Xquik exports, or the Twitter/X API. It normalizes provenance, enriches records with model-agnostic AI, validates the output schema, and writes JSONL, grouped JSON, and flattened CSV artifacts.

The local deterministic provider must always work without credentials.

## Important Files

| Path | Purpose |
|---|---|
| `twitter_etl.py` | Source loading, normalization, provider selection, enrichment, validation, and export writing |
| `social_signal_pipeline/sources.py` | Source loading, Twitter/X retry handling, normalization, and provenance helpers |
| `social_signal_pipeline/exports.py` | JSON/JSONL writing and CSV projection helpers |
| `twitter_dag.py` | Airflow 2 TaskFlow DAG entrypoint calling `run_twitter_etl()` |
| `dashboard.py` | Streamlit dashboard; reads JSONL first, CSV fallback second |
| `streaming/twitter_stream.py` | Optional Twitter/X filtered-stream to Kafka producer |
| `examples/sample_tweets.jsonl` | Safe fixture data for demos and tests |
| `tests/test_twitter_etl.py` | Regression tests for ingestion, provenance, schema, providers, fallback, and exports |
| `.env.example` | Supported runtime configuration |

## Data Safety Rules

- Never invent or overwrite source truth fields from model output.
- Preserve tweet IDs, source URLs, author handles, timestamps, metrics, connector names, and source confidence.
- Fixture/demo records must use `is_sample: true` and `source_confidence: sample`.
- Xquik exports without tweet IDs are exported data, not verified data.
- Use `signal_type: none` when there is no grounded signal.
- Set human review for high-risk toxicity, low-confidence extraction, or missing real-data identifiers.

## AI Provider Architecture

Supported providers are selected by environment variables:

```bash
AI_PROVIDER=local
AI_ENRICHMENT_MODE=local
AI_MODEL=local-rule-enricher-v1
AI_API_KEY=
AI_BASE_URL=
```

Provider classes live in `twitter_etl.py`:

- `BaseEnrichmentProvider`
- `LocalRuleProvider`
- `OpenAICompatibleProvider`
- `AnthropicProvider`
- local/open-provider wrappers such as Ollama, vLLM, LM Studio, Hugging Face, Together, Groq, and Fireworks

All provider output must pass `AiEnrichmentModel` validation before use. Invalid output falls back to `LocalRuleProvider`.

## Validation Commands

```bash
python -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py social_signal_pipeline/*.py
pytest -q
FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl \
OUTPUT_CSV_PATH=outputs/refined_tweets.csv \
OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl \
OUTPUT_JSON_PATH=outputs/enriched_tweets.json \
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Current Technical Debt

- Provider and schema internals should eventually be split out of `twitter_etl.py`.
- A future Airflow DAG variant can use separate extract, enrich, validate, and export tasks.
- Dashboard tests should be added once the UI is promoted beyond demo/portfolio use.
