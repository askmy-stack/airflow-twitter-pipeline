# Contributing

Thanks for helping improve this Airflow Twitter/X pipeline.

## Local setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest
```

## Run the no-credential demo

```bash
cp .env.example .env
export FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl
export OUTPUT_CSV_PATH=outputs/refined_tweets.csv
export OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl
export OUTPUT_JSON_PATH=outputs/enriched_tweets.json
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Validate changes

```bash
python -m py_compile twitter_etl.py twitter_dag.py
PYTHONPATH=. pytest tests/ -q
```

## Pull request checklist

- Keep real tweet provenance intact; never present generated/sample text as verified real tweets.
- Add or update tests for behavior changes.
- Update README or `.env.example` when configuration changes.
- Do not commit `.env`, API keys, generated outputs, or local Airflow runtime files.
