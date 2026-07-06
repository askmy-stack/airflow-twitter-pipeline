from __future__ import annotations

from datetime import datetime, timedelta

from airflow.decorators import dag, task

from twitter_etl import run_twitter_etl


DEFAULT_ARGS = {
    "owner": "airflow",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1),
}


@dag(
    dag_id="twitter_dag",
    default_args=DEFAULT_ARGS,
    description="Ingest, enrich, validate, and export Twitter/X signal intelligence.",
    schedule=timedelta(days=1),
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["twitter", "ai-enrichment", "social-signals"],
)
def social_signal_pipeline_dag():
    @task(task_id="run_twitter_etl")
    def run_pipeline():
        return run_twitter_etl()

    run_pipeline()


twitter_dag = social_signal_pipeline_dag()
