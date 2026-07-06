#!/usr/bin/env bash
set -euo pipefail

python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

export FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl
export AI_PROVIDER=local
export AI_ENRICHMENT_MODE=local
export OUTPUT_CSV_PATH=outputs/refined_tweets.csv
export OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl
export OUTPUT_JSON_PATH=outputs/enriched_tweets.json

python -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py social_signal_pipeline/*.py
pytest -q
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
