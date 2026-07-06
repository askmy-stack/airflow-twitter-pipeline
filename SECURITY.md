# Security Policy

## Supported Versions

Security fixes target the default branch until versioned releases are published. After releases begin, supported versions will be listed here.

## Reporting A Vulnerability

Please do not disclose vulnerabilities publicly before maintainers have had a chance to respond.

Preferred reporting path:

1. Open a private security advisory on GitHub if available.
2. If private advisories are unavailable, contact the maintainer through the repository owner profile.

Do not include API keys, tokens, private tweet exports, or private tweet text in public issues.

## Secrets And Credentials

Credentials must come from environment variables, local `.env` files, Airflow configuration, or deployment secret stores. Never hardcode or commit:

- Twitter/X credentials
- AI provider API keys
- Kafka credentials
- private exports
- generated output files
- local Airflow runtime files

The repository ignores `.env`, `outputs/`, `exports/`, local Airflow files, and common Python caches by default.

## Data Safety

- Real tweet records require source metadata.
- Fixture/demo tweets must be marked as sample data.
- Model output must not overwrite tweet IDs, URLs, authors, metrics, source connectors, or source confidence.
- Unsupported market or social claims should use `signal_type: none`.
- High toxicity, low-confidence extraction, or missing real-data identifiers should require human review.

## Dependency Hygiene

Run validation before publishing changes:

```bash
python -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py social_signal_pipeline/*.py
pytest -q
```
