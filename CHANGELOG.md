# Changelog

All notable changes to Social Signal Pipeline will be documented in this file.

This project follows a lightweight version of Keep a Changelog. Versioned releases will begin once the enrichment schema is stable.

## Unreleased

### Added

- Model-agnostic AI enrichment provider layer.
- Provider configuration through `AI_PROVIDER`, `AI_ENRICHMENT_MODE`, `AI_MODEL`, `AI_API_KEY`, and `AI_BASE_URL`.
- Pydantic validation for AI enrichment output.
- Local deterministic fallback for malformed, invalid, unavailable, or unconfigured model providers.
- Quality metadata for `ai_provider`, `ai_model`, `enrichment_mode`, and `fallback_used`.
- Flattened analytics CSV fields for dashboarding.
- Professional README with visuals, architecture, schema, usage, roadmap, and production-readiness notes.
- Repository visual assets in `docs/assets/`.
- Package modules for source ingestion and export projection/writing.
- Twitter/X API retry/backoff with logging.
- Airflow 2 TaskFlow DAG.
- Tag-driven GitHub Release workflow.
- Provider and deployment guides.

### Changed

- CSV output is now generated from validated enriched records.
- Dashboard now prefers canonical JSONL output and falls back to CSV.
- CI compiles ETL, Airflow DAG, dashboard, and streaming modules.
- Project documentation now reflects the renamed `social-signal-pipeline` repository.
- `twitter_commands.sh` is now an executable validation/demo helper.

### Security

- Reinforced that source truth fields remain outside model control.
- Documented sample-data and private-export handling expectations.
