from __future__ import annotations

import logging
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.models import Variable

log = logging.getLogger(__name__)


def _sla_miss_callback(dag, task_list, blocking_task_list, slas, blocking_tis):  # noqa: ANN001
    log.error(
        "SLA missed on DAG '%s'. Missed tasks: %s. Blocking tasks: %s.",
        dag.dag_id,
        task_list,
        blocking_task_list,
    )


@dag(
    dag_id="twitter_pipeline",
    schedule="@daily",
    start_date=datetime(2024, 1, 1),
    catchup=False,
    default_args={
        "owner": "airflow",
        "retries": 2,
        "retry_delay": timedelta(minutes=5),
        "email_on_failure": False,
        "email_on_retry": False,
    },
    sla_miss_callback=_sla_miss_callback,
    description="Daily Twitter ETL — extract, LLM-enrich, validate, and load tweets.",
    tags=["twitter", "etl", "llm"],
)
def twitter_pipeline() -> None:
    """
    ### Twitter Data Pipeline

    Pulls recent tweets for a configurable target user (Airflow Variable
    ``twitter_target_user``, defaults to ``elonmusk``), enriches each tweet
    with Claude-powered sentiment / topic classification, validates the
    resulting DataFrame against a Pandera schema, then writes the output to
    S3 (when ``S3_BUCKET`` env var is set) or to a local CSV.

    **Required environment variables / Airflow Variables:**
    - ``TWITTER_BEARER_TOKEN``
    - ``TWITTER_CONSUMER_KEY`` / ``TWITTER_CONSUMER_SECRET``
    - ``TWITTER_ACCESS_TOKEN`` / ``TWITTER_ACCESS_SECRET``
    - ``ANTHROPIC_API_KEY``
    - ``S3_BUCKET`` *(optional — falls back to local CSV)*
    - Airflow Variable ``twitter_target_user`` *(optional, default: elonmusk)*
    """

    @task()
    def extract(screen_name: str) -> list[dict]:
        from twitter_etl import extract_tweets
        return extract_tweets(screen_name)

    @task()
    def enrich(tweets: list[dict]) -> list[dict]:
        from twitter_etl import enrich_with_llm
        return enrich_with_llm(tweets)

    @task()
    def load(tweets: list[dict]) -> None:
        from twitter_etl import validate_and_load
        validate_and_load(tweets)

    screen_name: str = Variable.get("twitter_target_user", default_var="elonmusk")
    raw = extract(screen_name)
    enriched = enrich(raw)
    load(enriched)


twitter_pipeline()
