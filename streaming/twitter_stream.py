"""
Real-time Twitter filtered-stream → Kafka producer.

Connects to the Twitter API v2 Filtered Stream endpoint, applies keyword
rules, and publishes each matching tweet as a JSON message to a Kafka topic
for downstream consumers (e.g. the Airflow KafkaConsumerOperator or a Flink
job).

Usage:
    python -m streaming.twitter_stream "#AI" "#SpaceX" "Elon Musk"

Environment variables (same as twitter_etl.py):
    TWITTER_BEARER_TOKEN       — required
    KAFKA_BOOTSTRAP_SERVERS    — default: localhost:9092
    KAFKA_TOPIC                — default: raw_tweets
"""
from __future__ import annotations

import json
import logging
import os
import sys

import tweepy
from kafka import KafkaProducer
from kafka.errors import KafkaError

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Kafka helpers
# ---------------------------------------------------------------------------

def _build_producer() -> KafkaProducer:
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    return KafkaProducer(
        bootstrap_servers=bootstrap,
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",               # strongest durability guarantee
        retries=5,
        linger_ms=20,             # micro-batch for throughput
    )


def _on_send_error(exc: KafkaError) -> None:
    log.error("Kafka delivery failed: %s", exc)


# ---------------------------------------------------------------------------
# Tweepy streaming client
# ---------------------------------------------------------------------------

class TweetStreamProducer(tweepy.StreamingClient):
    """Tweepy v2 streaming client that publishes tweets to a Kafka topic."""

    def __init__(self, bearer_token: str, producer: KafkaProducer, topic: str) -> None:
        super().__init__(bearer_token, wait_on_rate_limit=True)
        self._producer = producer
        self._topic = topic

    def on_tweet(self, tweet: tweepy.Tweet) -> None:
        payload = {
            "id": str(tweet.id),
            "text": tweet.text,
            "created_at": str(getattr(tweet, "created_at", None)),
            "author_id": str(getattr(tweet, "author_id", None)),
            "public_metrics": getattr(tweet, "public_metrics", {}),
        }
        self._producer.send(self._topic, value=payload).add_errback(_on_send_error)
        log.info("Produced tweet %s → topic '%s'", tweet.id, self._topic)

    def on_errors(self, errors: object) -> bool:
        log.error("Stream error: %s", errors)
        return False  # returning False stops the stream

    def on_disconnect(self) -> None:
        log.warning("Stream disconnected — flushing producer.")
        self._producer.flush()


# ---------------------------------------------------------------------------
# Rule management helpers
# ---------------------------------------------------------------------------

def _reset_rules(stream: TweetStreamProducer, keywords: list[str]) -> None:
    """Delete all existing stream rules and replace with *keywords*."""
    existing = stream.get_rules()
    if existing.data:
        ids = [r.id for r in existing.data]
        stream.delete_rules(ids)
        log.info("Deleted %d existing stream rules.", len(ids))

    new_rules = [tweepy.StreamRule(kw) for kw in keywords]
    resp = stream.add_rules(new_rules)
    if resp.errors:
        raise RuntimeError(f"Failed to add stream rules: {resp.errors}")
    log.info("Added %d stream rules: %s", len(new_rules), keywords)


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------

def start_stream(keywords: list[str], topic: str | None = None) -> None:
    """
    Start the filtered stream.  Blocks until the stream is disconnected or
    an unrecoverable error occurs.

    Args:
        keywords: List of filter keywords / phrases (Twitter operator syntax).
        topic:    Kafka topic to publish to.  Defaults to ``KAFKA_TOPIC`` env
                  var or ``"raw_tweets"``.
    """
    if not keywords:
        raise ValueError("At least one keyword is required.")

    topic = topic or os.environ.get("KAFKA_TOPIC", "raw_tweets")
    bearer_token = os.environ["TWITTER_BEARER_TOKEN"]

    producer = _build_producer()
    stream = TweetStreamProducer(bearer_token, producer, topic)

    _reset_rules(stream, keywords)

    log.info("Starting filtered stream → Kafka topic '%s' …", topic)
    stream.filter(
        tweet_fields=["created_at", "author_id", "public_metrics"],
    )


if __name__ == "__main__":
    _keywords = sys.argv[1:] if len(sys.argv) > 1 else ["#AI", "#SpaceX"]
    start_stream(_keywords)
