import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


SCHEMA_VERSION = "1.0"
LOCAL_ENRICHER_MODEL = "local-rule-enricher-v1"

ENTITY_TYPES = {
    "person",
    "company",
    "product",
    "technology",
    "asset",
    "place",
    "organization",
    "research_field",
    "other",
}
SENTIMENTS = {"positive", "negative", "neutral", "mixed"}
TOXICITY_LEVELS = {"none", "low", "medium", "high"}
INTENTS = {
    "news",
    "opinion",
    "research_update",
    "product_update",
    "market_commentary",
    "hiring",
    "funding",
    "warning",
    "question",
    "announcement",
    "other",
}
SIGNAL_TYPES = {
    "none",
    "bullish",
    "bearish",
    "adoption",
    "risk",
    "controversy",
    "technical_breakthrough",
    "funding",
    "policy",
    "infrastructure_shift",
}
SIGNAL_STRENGTHS = {"low", "medium", "high"}
DOMAINS = {
    "technology",
    "ai_ml",
    "research",
    "infrastructure",
    "finance",
    "cybersecurity",
    "cloud",
    "semiconductors",
    "crypto",
    "policy",
    "energy",
    "healthcare",
    "education",
    "other",
}
RELATIONSHIPS = {"direct", "indirect", "speculative"}

DOMAIN_KEYWORDS = {
    "ai_ml": {
        "ai",
        "agent",
        "agents",
        "artificial intelligence",
        "embedding",
        "eval",
        "llm",
        "machine learning",
        "model",
        "neural",
        "rag",
        "transformer",
    },
    "research": {
        "arxiv",
        "benchmark",
        "dataset",
        "experiment",
        "paper",
        "preprint",
        "research",
        "study",
    },
    "infrastructure": {
        "airflow",
        "cluster",
        "datacenter",
        "etl",
        "infrastructure",
        "kafka",
        "kubernetes",
        "latency",
        "pipeline",
        "reliability",
        "server",
    },
    "finance": {
        "earnings",
        "equity",
        "finance",
        "fund",
        "guidance",
        "market",
        "nasdaq",
        "revenue",
        "stock",
        "valuation",
    },
    "cybersecurity": {
        "breach",
        "cve",
        "exploit",
        "malware",
        "phishing",
        "ransomware",
        "security",
        "vulnerability",
        "zero-day",
    },
    "cloud": {"aws", "azure", "cloud", "gcp", "serverless", "snowflake"},
    "semiconductors": {
        "asic",
        "chip",
        "gpu",
        "h100",
        "nvidia",
        "semiconductor",
        "tpu",
    },
    "crypto": {"bitcoin", "blockchain", "crypto", "defi", "ethereum", "token"},
    "policy": {"congress", "policy", "regulation", "regulator", "senate", "tariff"},
    "energy": {"battery", "energy", "grid", "nuclear", "solar", "wind"},
    "healthcare": {"clinical", "drug", "fda", "health", "healthcare", "patient"},
    "education": {"course", "education", "learning", "school", "student", "teaching"},
    "technology": {
        "api",
        "app",
        "code",
        "developer",
        "github",
        "platform",
        "release",
        "software",
        "technology",
    },
}

ENTITY_KEYWORDS = {
    "OpenAI": "company",
    "Anthropic": "company",
    "Google": "company",
    "Microsoft": "company",
    "Amazon": "company",
    "AWS": "company",
    "NVIDIA": "company",
    "Tesla": "company",
    "Apple": "company",
    "Meta": "company",
    "Bitcoin": "asset",
    "Ethereum": "asset",
    "Airflow": "technology",
    "Kafka": "technology",
    "Kubernetes": "technology",
    "Python": "technology",
    "DuckDB": "technology",
    "S3": "technology",
    "LLM": "technology",
    "RAG": "technology",
    "GPU": "technology",
}

POSITIVE_WORDS = {
    "adoption",
    "breakthrough",
    "gain",
    "growth",
    "improve",
    "improved",
    "launch",
    "record",
    "strong",
    "surge",
}
NEGATIVE_WORDS = {
    "breach",
    "delay",
    "drop",
    "failed",
    "loss",
    "outage",
    "risk",
    "slowdown",
    "warning",
    "weak",
}
TOXIC_WORDS = {"hate", "kill", "racist", "threat", "violent"}


def run_twitter_etl():
    rows = load_source_rows()
    normalized_rows = [_normalize_tweet(row) for row in rows]
    normalized_rows = [row for row in normalized_rows if row["text"]]

    output_path = Path(os.getenv("OUTPUT_CSV_PATH", "refined_tweets.csv"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_csv_projection(normalized_rows)).to_csv(output_path, index=False)

    enriched = enrich_tweets(normalized_rows)
    jsonl_path = Path(os.getenv("OUTPUT_JSONL_PATH", "outputs/enriched_tweets.jsonl"))
    json_path = Path(os.getenv("OUTPUT_JSON_PATH", "outputs/enriched_tweets.json"))
    write_enriched_outputs(enriched, jsonl_path=jsonl_path, json_path=json_path)

    return {
        "csv": str(output_path),
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "records": len(enriched),
    }


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

    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_token, access_secret)

    api = tweepy.API(auth)
    tweets = api.user_timeline(
        screen_name=screen_name,
        count=max(1, min(count, 200)),
        include_rts=False,
        tweet_mode="extended",
    )
    return [tweet._json for tweet in tweets]


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


def enrich_tweets(normalized_rows):
    return [enrich_tweet(row) for row in normalized_rows]


def enrich_tweet(row):
    ai_model = LOCAL_ENRICHER_MODEL
    ai_enrichment = None
    if os.getenv("OPENAI_API_KEY"):
        ai_enrichment = _try_openai_enrichment(row)
        if ai_enrichment:
            ai_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    if ai_enrichment is None:
        ai_enrichment = _local_ai_enrichment(row["text"])

    domain_analysis = _domain_analysis(row["text"], ai_enrichment)
    record = {
        "tweet": _tweet_payload(row),
        "ai_enrichment": ai_enrichment,
        "domain_analysis": domain_analysis,
        "quality": {
            "schema_version": SCHEMA_VERSION,
            "ai_model": ai_model,
            "validated": False,
            "validation_errors": [],
            "requires_human_review": _requires_human_review(row, ai_enrichment, domain_analysis),
        },
    }
    errors = validate_enriched_record(record)
    record["quality"]["validation_errors"] = errors
    record["quality"]["validated"] = not errors
    if errors:
        record["quality"]["requires_human_review"] = True
    return record


def write_enriched_outputs(records, jsonl_path, json_path):
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    grouped = {
        "metadata": {
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "record_count": len(records),
        },
        "records": records,
    }
    json_path.write_text(
        json.dumps(grouped, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def validate_enriched_record(record):
    errors = []
    tweet = record.get("tweet", {})
    ai = record.get("ai_enrichment", {})
    domain = record.get("domain_analysis", {})
    quality = record.get("quality", {})

    _require(tweet, "text", errors)
    _require(tweet, "author_handle", errors)
    _require(tweet, "created_at", errors)
    _require(tweet, "ingested_at", errors)
    if tweet.get("source_connector") not in {"twitter_api", "xquik", "fixture"}:
        errors.append("tweet.source_connector is invalid")
    if tweet.get("source_confidence") not in {"verified", "exported", "sample"}:
        errors.append("tweet.source_confidence is invalid")
    if tweet.get("source_confidence") == "verified" and not tweet.get("tweet_id"):
        errors.append("verified tweets require tweet_id")
    if tweet.get("is_sample") and tweet.get("source_confidence") != "sample":
        errors.append("sample tweets must use sample source_confidence")

    if ai.get("sentiment") not in SENTIMENTS:
        errors.append("ai_enrichment.sentiment is invalid")
    if ai.get("intent") not in INTENTS:
        errors.append("ai_enrichment.intent is invalid")
    toxicity = ai.get("toxicity_risk", {})
    if toxicity.get("level") not in TOXICITY_LEVELS:
        errors.append("ai_enrichment.toxicity_risk.level is invalid")
    _validate_score(toxicity.get("score"), "ai_enrichment.toxicity_risk.score", errors)
    signal = ai.get("market_or_social_signal", {})
    if signal.get("signal_type") not in SIGNAL_TYPES:
        errors.append("ai_enrichment.market_or_social_signal.signal_type is invalid")
    if signal.get("strength") not in SIGNAL_STRENGTHS:
        errors.append("ai_enrichment.market_or_social_signal.strength is invalid")
    for index, entity in enumerate(ai.get("entities", [])):
        if entity.get("type") not in ENTITY_TYPES:
            errors.append(f"ai_enrichment.entities[{index}].type is invalid")
        _validate_score(entity.get("confidence"), f"ai_enrichment.entities[{index}].confidence", errors)

    if domain.get("primary_domain") not in DOMAINS:
        errors.append("domain_analysis.primary_domain is invalid")
    _validate_score(domain.get("relevance_score"), "domain_analysis.relevance_score", errors)
    for index, correlated in enumerate(domain.get("correlated_domains", [])):
        if correlated.get("domain") not in DOMAINS:
            errors.append(f"domain_analysis.correlated_domains[{index}].domain is invalid")
        if correlated.get("relationship") not in RELATIONSHIPS:
            errors.append(f"domain_analysis.correlated_domains[{index}].relationship is invalid")

    if quality.get("schema_version") != SCHEMA_VERSION:
        errors.append("quality.schema_version is invalid")
    return errors


def _normalize_tweet(tweet):
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
        "created_at": _normalize_datetime(_first_value(tweet, "created_at", "createdAt", "createdAtIso")),
        "ingested_at": _now_iso(),
        "language": _first_value(tweet, "lang", "language") or None,
        "metrics": {
            "likes": _to_int(_first_value(tweet, "favorite_count", "like_count", "likes")),
            "retweets": _to_int(_first_value(tweet, "retweet_count", "retweets")),
            "replies": _to_int(_first_value(tweet, "reply_count", "replies")),
            "quotes": _to_int(_first_value(tweet, "quote_count", "quotes")),
        },
        "source_connector": connector,
        "source_confidence": source_confidence,
        "is_sample": is_sample,
    }


def _normalise_tweets(tweets):
    rows = []
    for tweet in tweets:
        normalized = _normalize_tweet(tweet)
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


def _tweet_payload(row):
    return {
        "tweet_id": row["tweet_id"],
        "source_url": row["source_url"],
        "author_handle": row["author_handle"],
        "author_name": row["author_name"],
        "text": row["text"],
        "created_at": row["created_at"],
        "ingested_at": row["ingested_at"],
        "language": row["language"],
        "metrics": row["metrics"],
        "source_connector": row["source_connector"],
        "source_confidence": row["source_confidence"],
        "is_sample": row["is_sample"],
    }


def _local_ai_enrichment(text):
    lowered = text.lower()
    sentiment = _sentiment(lowered)
    topics = _topics(lowered)
    entities = _entities(text)
    toxicity = _toxicity(lowered)
    intent = _intent(lowered)
    signal = _market_or_social_signal(lowered)
    return {
        "sentiment": sentiment,
        "topics": topics,
        "entities": entities,
        "summary": _summary(text),
        "toxicity_risk": toxicity,
        "intent": intent,
        "market_or_social_signal": signal,
    }


def _try_openai_enrichment(row):
    try:
        from openai import OpenAI

        client = OpenAI()
        response = client.responses.create(
            model=os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
            input=[
                {
                    "role": "system",
                    "content": (
                        "Return only valid JSON for one tweet. Do not invent facts, "
                        "source URLs, metrics, or market signals. Use 'none' when "
                        "the tweet does not support a signal."
                    ),
                },
                {"role": "user", "content": json.dumps(_tweet_payload(row), ensure_ascii=False)},
            ],
            text={"format": {"type": "json_object"}},
        )
        content = getattr(response, "output_text", "")
        parsed = json.loads(content)
        if validate_enriched_record(
            {
                "tweet": _tweet_payload(row),
                "ai_enrichment": parsed,
                "domain_analysis": _domain_analysis(row["text"], parsed),
                "quality": {
                    "schema_version": SCHEMA_VERSION,
                    "ai_model": os.getenv("OPENAI_MODEL", "gpt-5.4-mini"),
                },
            }
        ):
            return None
        return parsed
    except Exception:
        return None


def _domain_analysis(text, ai_enrichment):
    lowered = text.lower()
    scores = {}
    for domain, keywords in DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for keyword in keywords if keyword in lowered)
    primary = max(scores, key=scores.get)
    if scores[primary] == 0:
        primary = "other"
    secondary = [
        domain
        for domain, score in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if domain != primary and score > 0
    ][:4]
    correlated = []
    for domain in secondary[:3]:
        correlated.append(
            {
                "domain": domain,
                "relationship": "direct" if scores[domain] > 1 else "indirect",
                "reason": f"Tweet contains terms associated with {domain.replace('_', ' ')}.",
            }
        )
    signal = ai_enrichment.get("market_or_social_signal", {}).get("signal_type", "none")
    if signal in {"bullish", "bearish", "funding"} and primary != "finance" and "finance" not in secondary:
        correlated.append(
            {
                "domain": "finance",
                "relationship": "speculative",
                "reason": "Market language is present, but the tweet is not primarily financial.",
            }
        )
    relevance_score = min(1.0, (scores.get(primary, 0) + len(secondary)) / 5)
    if primary == "other":
        relevance_score = 0.1
    return {
        "primary_domain": primary,
        "secondary_domains": secondary,
        "correlated_domains": correlated,
        "relevance_score": round(relevance_score, 2),
    }


def _sentiment(lowered):
    positive = sum(1 for word in POSITIVE_WORDS if word in lowered)
    negative = sum(1 for word in NEGATIVE_WORDS if word in lowered)
    if positive and negative:
        return "mixed"
    if positive:
        return "positive"
    if negative:
        return "negative"
    return "neutral"


def _topics(lowered):
    topics = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            topics.append(domain)
    return topics[:6] or ["general"]


def _entities(text):
    entities = []
    lowered = text.lower()
    for name, entity_type in ENTITY_KEYWORDS.items():
        if name.lower() in lowered:
            entities.append({"name": name, "type": entity_type, "confidence": 0.85})
    return entities


def _toxicity(lowered):
    matches = [word for word in TOXIC_WORDS if word in lowered]
    if not matches:
        return {"level": "none", "score": 0.0, "reason": "No toxicity indicators detected."}
    score = min(1.0, 0.35 * len(matches))
    level = "low" if score < 0.4 else "medium" if score < 0.75 else "high"
    return {"level": level, "score": round(score, 2), "reason": "Potentially harmful language detected."}


def _intent(lowered):
    if "?" in lowered:
        return "question"
    if any(word in lowered for word in ("hiring", "role", "job")):
        return "hiring"
    if any(word in lowered for word in ("funding", "raised", "series a", "series b")):
        return "funding"
    if any(word in lowered for word in ("launch", "released", "shipping", "introducing")):
        return "product_update"
    if any(word in lowered for word in ("paper", "research", "benchmark", "study")):
        return "research_update"
    if any(word in lowered for word in ("stock", "market", "earnings", "revenue")):
        return "market_commentary"
    if any(word in lowered for word in ("warning", "risk", "breach", "outage")):
        return "warning"
    if any(word in lowered for word in ("announcing", "announcement", "today we")):
        return "announcement"
    if any(word in lowered for word in ("i think", "opinion", "imo")):
        return "opinion"
    return "news"


def _market_or_social_signal(lowered):
    if any(word in lowered for word in ("breach", "outage", "risk", "warning", "vulnerability")):
        return {
            "signal_type": "risk",
            "strength": "medium",
            "rationale": "The tweet includes risk or reliability language.",
        }
    if any(word in lowered for word in ("funding", "raised", "series a", "series b")):
        return {
            "signal_type": "funding",
            "strength": "medium",
            "rationale": "The tweet refers to company financing activity.",
        }
    if any(word in lowered for word in ("adoption", "customers", "users", "deployment")):
        return {
            "signal_type": "adoption",
            "strength": "medium",
            "rationale": "The tweet references adoption or deployment.",
        }
    if any(word in lowered for word in ("breakthrough", "state of the art", "sota")):
        return {
            "signal_type": "technical_breakthrough",
            "strength": "medium",
            "rationale": "The tweet claims a technical advance.",
        }
    if any(word in lowered for word in ("regulation", "policy", "senate", "congress")):
        return {
            "signal_type": "policy",
            "strength": "medium",
            "rationale": "The tweet references policy or regulation.",
        }
    if any(word in lowered for word in ("bullish", "surge", "record high", "beat earnings")):
        return {
            "signal_type": "bullish",
            "strength": "medium",
            "rationale": "The tweet includes positive market language.",
        }
    if any(word in lowered for word in ("bearish", "missed earnings", "selloff", "slump")):
        return {
            "signal_type": "bearish",
            "strength": "medium",
            "rationale": "The tweet includes negative market language.",
        }
    return {
        "signal_type": "none",
        "strength": "low",
        "rationale": "No grounded market or social signal detected.",
    }


def _summary(text):
    clean = " ".join(str(text).split())
    if len(clean) <= 220:
        return clean
    return clean[:217].rstrip() + "..."


def _requires_human_review(row, ai_enrichment, domain_analysis):
    toxicity = ai_enrichment.get("toxicity_risk", {})
    if toxicity.get("level") in {"medium", "high"}:
        return True
    if row["source_confidence"] != "verified" and not row["is_sample"] and not row["tweet_id"]:
        return True
    return domain_analysis.get("relevance_score", 0) < 0.2


def _csv_projection(rows):
    projected = []
    for row in rows:
        projected.append(
            {
                "tweet_id": row["tweet_id"],
                "user": row["author_handle"],
                "text": row["text"],
                "favorite_count": row["metrics"]["likes"],
                "retweet_count": row["metrics"]["retweets"],
                "created_at": row["created_at"],
                "source_connector": row["source_connector"],
                "source_confidence": row["source_confidence"],
                "is_sample": row["is_sample"],
            }
        )
    return projected


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


def _normalize_datetime(value):
    if not value:
        return _now_iso()
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


def _now_iso():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _to_int(value):
    if value in (None, ""):
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _require(data, key, errors):
    if data.get(key) in (None, ""):
        errors.append(f"{key} is required")


def _validate_score(value, path, errors):
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        errors.append(f"{path} must be between 0 and 1")


def _required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is required when no fixture or Xquik path is set")
    return value
