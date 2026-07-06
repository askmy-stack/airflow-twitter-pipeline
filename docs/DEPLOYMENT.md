# Deployment Guide

This guide covers practical deployment paths for Social Signal Pipeline.

## Local Demo

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

export FIXTURE_TWEETS_PATH=examples/sample_tweets.jsonl
export AI_PROVIDER=local
export AI_ENRICHMENT_MODE=local
python -c "from twitter_etl import run_twitter_etl; print(run_twitter_etl())"
```

## Docker Compose

```bash
cp .env.example .env
docker compose up -d
```

Services:

- Airflow: `http://localhost:8080`
- Streamlit dashboard: `http://localhost:8501`
- Kafka: `localhost:9092`

## Airflow

The repository includes an Airflow 2 TaskFlow DAG in `twitter_dag.py`.

Recommended production settings:

- Store credentials in Airflow Connections, environment variables, or your platform secret manager.
- Keep generated output paths on durable storage.
- Configure task-level retries and alerting in Airflow.
- Use the fixture path for smoke tests before enabling live Twitter/X ingestion.

## Managed Airflow

For MWAA, Cloud Composer, or Astronomer:

1. Package or sync this repository as a DAG bundle.
2. Configure environment variables or provider secrets.
3. Mount/write outputs to durable object storage.
4. Trigger `twitter_dag`.
5. Monitor task logs for retry/backoff behavior on live API calls.

## Release Process

Releases are tag-driven:

```bash
cat VERSION
git tag v0.1.0
git push origin v0.1.0
```

The release workflow verifies that the pushed tag matches `VERSION` and publishes a GitHub Release.

## Operational Hardening Checklist

- Use local fixtures for deployment smoke tests.
- Use least-privilege API keys and rotate credentials regularly.
- Keep private exports outside the repository.
- Monitor live API rate limits and failures.
- Keep `CHANGELOG.md` updated before tagging a release.
