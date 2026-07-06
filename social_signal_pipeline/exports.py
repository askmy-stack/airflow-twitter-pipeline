import json

from .sources import now_iso


def write_enriched_outputs(records, jsonl_path, json_path, schema_version):
    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    grouped = {
        "metadata": {
            "schema_version": schema_version,
            "generated_at": now_iso(),
            "record_count": len(records),
        },
        "records": records,
    }
    json_path.write_text(
        json.dumps(grouped, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def csv_projection(rows):
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


def enriched_csv_projection(records):
    projected = []
    for record in records:
        tweet = record["tweet"]
        ai = record["ai_enrichment"]
        domain = record["domain_analysis"]
        quality = record["quality"]
        signal = ai["market_or_social_signal"]
        toxicity = ai["toxicity_risk"]
        projected.append(
            {
                "tweet_id": tweet["tweet_id"],
                "user": tweet["author_handle"],
                "text": tweet["text"],
                "favorite_count": tweet["metrics"]["likes"],
                "retweet_count": tweet["metrics"]["retweets"],
                "reply_count": tweet["metrics"]["replies"],
                "quote_count": tweet["metrics"]["quotes"],
                "created_at": tweet["created_at"],
                "source_connector": tweet["source_connector"],
                "source_confidence": tweet["source_confidence"],
                "is_sample": tweet["is_sample"],
                "sentiment": ai["sentiment"],
                "topics": json.dumps(ai["topics"], ensure_ascii=False),
                "summary": ai["summary"],
                "intent": ai["intent"],
                "toxicity_level": toxicity["level"],
                "toxicity_score": toxicity["score"],
                "signal_type": signal["signal_type"],
                "signal_strength": signal["strength"],
                "primary_domain": domain["primary_domain"],
                "secondary_domains": json.dumps(domain["secondary_domains"], ensure_ascii=False),
                "relevance_score": domain["relevance_score"],
                "ai_provider": quality["ai_provider"],
                "ai_model": quality["ai_model"],
                "enrichment_mode": quality["enrichment_mode"],
                "fallback_used": quality["fallback_used"],
                "requires_human_review": quality["requires_human_review"],
                "validated": quality["validated"],
            }
        )
    return projected
