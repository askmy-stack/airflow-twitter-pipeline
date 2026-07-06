## Summary

Explain what changed and why.

## Type of change

- [ ] Bug fix
- [ ] Feature
- [ ] Documentation
- [ ] Refactor
- [ ] Test/CI
- [ ] Repository polish

## Validation

- [ ] `python -m py_compile twitter_etl.py twitter_dag.py dashboard.py streaming/twitter_stream.py`
- [ ] `PYTHONPATH=. pytest tests/ -q`
- [ ] Fixture demo writes CSV, JSONL, and grouped JSON outputs

## Data safety

- [ ] No credentials, private exports, generated outputs, or local runtime files are committed
- [ ] Sample/demo tweets are clearly marked as sample data
- [ ] Real tweet provenance fields are preserved
- [ ] Model output cannot overwrite source truth fields

## Documentation

- [ ] README updated if behavior or configuration changed
- [ ] `.env.example` updated if environment variables changed
- [ ] CHANGELOG updated for user-facing behavior

## Screenshots or output

Paste relevant screenshots, dashboard previews, or command output when helpful.
