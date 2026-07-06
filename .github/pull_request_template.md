## Summary

## Validation

- [ ] `python -m py_compile twitter_etl.py twitter_dag.py`
- [ ] `PYTHONPATH=. pytest tests/ -q`
- [ ] Fixture demo still writes CSV, JSONL, and JSON outputs

## Data safety

- [ ] No credentials or private exports are committed
- [ ] Sample/demo tweets are clearly marked as sample data
- [ ] Real tweet provenance fields are preserved
