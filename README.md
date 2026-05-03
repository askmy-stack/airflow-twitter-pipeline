# airflow-twitter-pipeline

> Twitter/X data ingestion pipeline orchestrated with Apache Airflow.

End-to-end ETL pipeline that collects tweets via the Twitter/X API and orchestrates the full workflow using Airflow DAGs with scheduling and retry logic.

## What it does

- Authenticates with Twitter/X API v2
- Collects tweets on configurable search terms or user timelines
- Transforms raw JSON responses into structured records
- Orchestrates the full ETL cycle via Airflow DAGs

## Stack

- **Languages:** Python
- **Orchestration:** Apache Airflow
- **APIs:** Twitter/X API v2

## Setup

```bash
git clone https://github.com/askmy-stack/airflow-twitter-pipeline.git
cd airflow-twitter-pipeline
pip install -r requirements.txt
export AIRFLOW_HOME=$(pwd)/airflow
airflow db init
airflow webserver &
airflow scheduler &
```

## What I learned

Airflow's DAG-based scheduling adds retry logic and observability to an otherwise brittle API polling loop. Discrete task boundaries make it easy to pinpoint failures at a specific stage.

## License

MIT

---

Built by [Abhinaysai Kamineni](https://github.com/askmy-stack)
