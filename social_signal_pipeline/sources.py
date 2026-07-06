import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)


def load_source_rows():
    fixture_path = os.getenv("FIXTURE_TWEETS_PATH") or os.getenv("SAMPLE_TWEETS_PATH")
    xquik_path = os.getenv("XQUIK_TWEETS_PATH")
    if fixture_path:
        return _tag_rows(load_export_rows(fixture_path, source_name="fixture"), "fixture", is_sample=True)
    if xquik_path:
        return _tag_rows(load_export_rows(xquik_path, source_name="Xquik"), "xquik", is_sample=False)
    return _tag_rows(fetch_twitter_rows(), "twitter_api", is_sample=False)


def fetch_twitter_rows():
    import tweepy

    consumer_key = _required_env("TWITTER_CONSUMER_KEY")
    consumer_secret = _required_env("TWITTER_CONSUMER_SECRET")
    access_token = _required_env("TWITTER_ACCESS_TOKEN")
    access_secret = _required_env("TWITTER_ACCESS_SECRET")
    screen_name = os.getenv("TWITTER_SCREEN_NAME", "@elonmusk")
    count = int(os.getenv("TWITTER_MAX_COUNT", "200"))
    max_attempts = int(os.getenv("TWITTER_API_MAX_ATTEMPTS", "3"))
    base_delay = float(os.getenv("TWITTER_API_RETRY_SECONDS", "2"))

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)

    api = tweepy.API(auth, wait_on_rate_limit=True)
    for attempt in range(1, max_attempts + 1):
        try:
            log.info("Fetching tweets for %s via Twitter/X API, attempt %s/%s", screen_name, attempt, max_attempts)
            tweets = api.user_timeline(
                screen_name=screen_name,
                count=max(1, min(count, 200)),
                include_rts=False,
                tweet_mode="extended",
            )
            return [tweet._json for tweet in tweets]
        except Exception:
            if attempt >= max_attempts:
                log.exception("Twitter/X API fetch failed after %s attempts", max_attempts)
                raise
            delay = base_delay * (2 ** (attempt - 1))
            log.warning("Twitter/X API fetch failed; retrying in %.1fs", delay, exc_info=True)
            time.sleep(delay)
    return []


def load_export_rows(path, source_name="export"):
    source = Path(path)
    if not source.exists():
        raise FileNotFoundError(f"{source_name} export not found: {source}")
    if source.suffix.lower() == ".csv":
        return pd.read_csv(source).to_dict(orient="records")
    raw = source.read_text(encoding="utf-8").strip()
    if not raw:
        return []
    if source.suffix.lower() == ".jsonl":
        return [json.loads(line) for line in raw.splitlines() if line.strip()]
    payload = json.loads(raw)
    if isinstance(payload, dict):
        for key in ("data", "tweets", "items", "results"):
            if isinstance(payload.get(key), list):
                return payload[key]
    if isinstance(payload, list):
        return payload
    raise ValueError(f"{source_name} export must be a JSON array, JSONL file, or CSV file")


def load_xquik_rows(path):
    return load_export_rows(path, source_name="Xquik")


def normalize_tweet(tweet):
    user = tweet.get("user") if isinstance(tweet.get("user"), dict) else {}
    author = tweet.get("author") if isinstance(tweet.get("author"), dict) else {}
    identity = user or author or tweet
    connector = tweet.get("_source_connector", "xquik")
    is_sample = bool(tweet.get("_is_sample") or tweet.get("is_sample"))
    tweet_id = str(_first_value(tweet, "id", "tweet_id", "tweetId", "rest_id") or "")
    author_handle = str(_first_value(identity, "screen_name", "screenName", "username", "handle") or "")
    if author_handle.startswith("@"):
        author_handle = author_handle[1:]
    source_confidence = _source_confidence(connector, tweet_id, is_sample)
    return {
        "tweet_id": tweet_id,
        "source_url": _source_url(tweet, tweet_id, author_handle),
        "author_handle": author_handle or "unknown",
        "author_name": _first_value(identity, "name", "display_name", "displayName") or None,
        "text": _first_value(tweet, "full_text", "fullText", "text", "content") or "",
        "created_at": normalize_datetime(_first_value(tweet, "created_at", "createdAt", "createdAtIso")),
        "ingested_at": now_iso(),
        "language": _first_value(tweet, "lang", "language") or None,
        "metrics": {
            "likes": to_int(_first_value(tweet, "favorite_count", "like_count", "likes")),
            "retweets": to_int(_first_value(tweet, "retweet_count", "retweets")),
            "replies": to_int(_first_value(tweet, "reply_count", "replies")),
            "quotes": to_int(_first_value(tweet, "quote_count", "quotes")),
        },
        "source_connector": connector,
        "source_confidence": source_confidence,
        "is_sample": is_sample,
    }


def normalise_tweets(tweets):
    rows = []
    for tweet in tweets:
        normalized = normalize_tweet(tweet)
        if not normalized["text"]:
            continue
        rows.append(
            {
                "user": normalized["author_handle"],
                "text": normalized["text"],
                "favorite_count": normalized["metrics"]["likes"],
                "retweet_count": normalized["metrics"]["retweets"],
                "created_at": normalized["created_at"],
            }
        )
    return rows


def _tag_rows(rows, connector, is_sample):
    tagged = []
    for row in rows:
        copied = dict(row)
        copied["_source_connector"] = connector
        copied["_is_sample"] = is_sample
        tagged.append(copied)
    return tagged


def _source_confidence(connector, tweet_id, is_sample):
    if is_sample or connector == "fixture":
        return "sample"
    if connector == "twitter_api" and tweet_id:
        return "verified"
    return "exported"


def _source_url(tweet, tweet_id, author_handle):
    explicit = _first_value(tweet, "source_url", "url", "tweet_url", "tweetUrl")
    if explicit:
        return explicit
    if tweet_id and author_handle:
        return f"https://twitter.com/{author_handle}/status/{tweet_id}"
    return None


def _first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return value
    return ""


def normalize_datetime(value):
    if not value:
        return now_iso()
    if isinstance(value, datetime):
        dt = value
    else:
        text = str(value).strip()
        try:
            dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return text
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def to_int(value):
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required when no fixture or Xquik path is set")
    return value
