# airflow-twitter-pipeline

[![CI](https://github.com/askmy-stack/airflow-twitter-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/askmy-stack/airflow-twitter-pipeline/actions/workflows/ci.yml)

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
- **AI:** Optional OpenAI enrichment with local deterministic fallback

## Setup

```bash
git clone https://github.com/askmy-stack/airflow-twitter-pipeline.git
cd airflow-twitter-pipeline
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
- `quality`: schema version, model name, validation status, validation errors, and human-review flag

If `OPENAI_API_KEY` is present, the enrichment step attempts structured OpenAI enrichment. If it is absent or the model output fails validation, the pipeline uses a deterministic local classifier so tests and demos still run.

## Validate changes

```bash
python -m py_compile twitter_etl.py twitter_dag.py
PYTHONPATH=. pytest tests/ -q
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Please keep tweet provenance intact, mark demo data as sample data, and never commit credentials or private exports.
