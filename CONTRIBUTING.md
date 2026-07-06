# Contributing

Thanks for helping improve Social Signal Pipeline. This project is built around one rule: preserve source truth. Model output may enrich tweets, but it must never invent provenance.

## Good First Contributions

- Add a source connector or Xquik export variant.
- Add an AI provider adapter or provider configuration example.
- Improve schema validation tests.
- Improve dashboard views for domains, signals, toxicity review, or provider quality.
- Improve documentation, examples, and onboarding.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install pytest
```

## Run The No-Credential Demo

```bash
export FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl
export AI_PROVIDER=local
export AI_ENRICHMENT_MODE=local
export OUTPUT_CSV_PATH=outputs/refined_tweets.csv
export OUTPUT_JSONL_PATH=outputs/enriched_tweets.jsonl
export OUTPUT_JSON_PATH=outputs/enriched_tweets.json
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Validate Changes

```bash
python -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py
PYTHONPATH=. pytest tests/ -q
```

## Data Safety Requirements

- Never commit `.env`, API keys, generated outputs, private exports, or local Airflow runtime files.
- Preserve `tweet_id`, `source_url`, `author_handle`, `created_at`, `source_connector`, and `source_confidence` when available.
- Mark fixture/demo records with `is_sample: true` and `source_confidence: sample`.
- Do not generate fake tweet text and present it as real.
- Use `signal_type: none` when the tweet does not support a market or social signal.
- Add tests for provider failures, malformed model output, and provenance-sensitive behavior.

## Pull Request Expectations

- Keep changes focused and explain the user impact.
- Include validation output in the PR body.
- Update `README.md`, `.env.example`, or `PROJECT_STATUS.md` when behavior or configuration changes.
- Update tests for new behavior.
- Keep generated output files out of the commit.

## Development Style

- Prefer small functions with explicit data flow.
- Prefer schema validation over ad hoc assumptions for model output.
- Keep provider-specific code behind provider classes.
- Keep the local deterministic path working without credentials.
- Preserve backwards-compatible helpers when practical.
