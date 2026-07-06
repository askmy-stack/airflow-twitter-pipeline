# Security Policy

## Supported versions

Security fixes target the default branch until versioned releases are published.

## Reporting a vulnerability

Please open a private security advisory on GitHub if available, or contact the maintainer through the repository owner profile.

Do not include API keys, tokens, or private tweet exports in public issues.

## Secret handling

Credentials must be provided through environment variables or local `.env` files. The repository ignores `.env`, generated outputs, local exports, and Airflow runtime files by default.
