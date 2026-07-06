# social-signal-pipeline

[![CI](https://github.com/askmy-stack/social-signal-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/askmy-stack/social-signal-pipeline/actions/workflows/ci.yml)

> Twitter/X data ingestion pipeline orchestrated with Apache Airflow.

End-to-end ETL pipeline that collects tweets via fixture data, Xquik exports, or the Twitter/X API, then normalizes, domain-classifies, enriches, and exports structured tweet intelligence artifacts.

## What it does

- Reads fixture JSONL for no-credential local demos
- Reads Xquik JSON, JSONL, or CSV tweet exports
- Falls back to live Twitter/X API ingestion when no source file is configured
- Preserves tweet provenance with source connector and source confidence fields
- Transforms raw JSON responses into structured CSV records
- Exports AI-enriched JSONL and grouped JSON records
- Classifies domains across tech, AI/ML, research, infrastructure, finance, cybersecurity, cloud, semiconductors, crypto, policy, energy, healthcare, education, and other
- Orchestrates the full ETL cycle via Airflow DAGs

## Stack

- **Languages:** Python
- **Orchestration:** Apache Airflow
- **APIs:** Twitter/X API v2
- **AI:** Model-agnostic enrichment with local rules, local LLMs, and OpenAI-compatible APIs

## Setup

```bash
git clone https://github.com/askmy-stack/social-signal-pipeline.git
cd social-signal-pipeline
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install apache-airflow pytest
export AIRFLOW_HOME=$(pwd)/airflow
airflow db init
airflow webserver &
airflow scheduler &
```

## Run locally without credentials

```bash
export FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl
export AI_PROVIDER=local
export OUTPUT_CSV_PATH=outputs/refined_tweets.csv
export OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl
export OUTPUT_JSON_PATH=outputs/enriched_tweets.json
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

Fixture records are always marked with `"is_sample": true` and `"source_confidence": "sample"`.

## Source configuration

Use Xquik export rows without live Twitter/X credentials:

```bash
export XQUIK_TWEETS_PATH=exports/xquik-tweets.jsonl
export OUTPUT_CSV_PATH=outputs/refined_tweets.csv
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

Use Twitter/X API credentials when neither `FIXTURE_TWEETS_PATH` nor `XQUIK_TWEETS_PATH` is set:

```bash
export TWITTER_CONSUMER_KEY=...
export TWITTER_CONSUMER_SECRET=...
export TWITTER_ACCESS_TOKEN=...
export TWITTER_ACCESS_SECRET=...
export TWITTER_SCREEN_NAME=@elonmusk
export TWITTER_MAX_COUNT=200
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Enriched JSON outputs

The pipeline writes two canonical enrichment artifacts:

- `outputs/enriched_tweets.jsonl`: one validated JSON object per tweet
- `outputs/enriched_tweets.json`: grouped export with metadata and records

Each enriched record includes:

- `tweet`: source truth, author, text, timestamps, metrics, connector, confidence, and sample flag
- `ai_enrichment`: sentiment, topics, entities, summary, toxicity risk, intent, and market/social signal
- `domain_analysis`: primary domain, secondary domains, correlations, and relevance score
- `quality`: schema version, provider, model, enrichment mode, fallback status, validation status, validation errors, and human-review flag

## Model-agnostic AI enrichment

The default enrichment path uses deterministic local rules, so tests and demos run without paid APIs:

```bash
export AI_PROVIDER=local
export AI_ENRICHMENT_MODE=local
export AI_MODEL=local-rule-enricher-v1
```

Use a local open source model through an OpenAI-compatible endpoint such as Ollama, vLLM, or LM Studio:

```bash
export AI_PROVIDER=ollama
export AI_ENRICHMENT_MODE=local_llm
export AI_MODEL=llama3.1
export AI_BASE_URL=http://localhost:11434/v1
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

Use hosted or commercial providers by setting `AI_PROVIDER`, `AI_MODEL`, and `AI_API_KEY`. Providers with OpenAI-compatible APIs can also set `AI_BASE_URL`.

```bash
export AI_PROVIDER=openai_compatible
export AI_ENRICHMENT_MODE=api
export AI_MODEL=provider/model-name
export AI_API_KEY=...
export AI_BASE_URL=https://api.provider.example/v1
```

Supported provider names are `local`, `openai`, `anthropic`, `ollama`, `huggingface`, `vllm`, `lmstudio`, `together`, `groq`, `fireworks`, and `openai_compatible`.

Supported enrichment modes are `local`, `api`, `local_llm`, and `hybrid`. Use `hybrid` when you want local rules as the baseline while accepting a validated model result from the configured provider.

Every model response is validated with the enrichment schema before it is trusted. Malformed JSON, missing fields, invalid enum values, unsupported domains, and unconfigured providers fall back to local rules. The model never controls source truth fields such as tweet IDs, URLs, authors, metrics, or connector confidence.

## Validate changes

```bash
python -m py_compile twitter_etl.py twitter_dag.py
PYTHONPATH=. pytest tests/ -q
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please keep tweet provenance intact, mark demo data as sample data, and never commit credentials or private exports.
