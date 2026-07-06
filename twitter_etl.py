import json
import os
from abc import ABC, abstractmethod
from pathlib import Path

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from social_signal_pipeline.exports import (
    csv_projection as _csv_projection,
    enriched_csv_projection as _enriched_csv_projection,
    write_enriched_outputs as _write_enriched_outputs,
)
from social_signal_pipeline.sources import (
    fetch_twitter_rows,
    load_export_rows,
    load_source_rows,
    load_xquik_rows,
    normalize_datetime as _normalize_datetime,
    normalize_tweet as _normalize_tweet,
    normalise_tweets as _normalise_tweets,
    now_iso as _now_iso,
    to_int as _to_int,
)


SCHEMA_VERSION = "1.0"
LOCAL_ENRICHER_MODEL = "local-rule-enricher-v1"
LOCAL_PROVIDER = "local"
ENRICHMENT_MODES = {"local", "api", "local_llm", "hybrid"}
SUPPORTED_AI_PROVIDERS = {
    "local",
    "openai",
    "anthropic",
    "ollama",
    "huggingface",
    "vllm",
    "lmstudio",
    "together",
    "groq",
    "fireworks",
    "openai_compatible",
}
LOCAL_LLM_PROVIDERS = {"ollama", "vllm", "lmstudio"}

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


class ToxicityRiskModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    score: float = Field(ge=0.0, le=1.0)
    reason: str

    @field_validator("level")
    @classmethod
    def validate_level(cls, value):
        if value not in TOXICITY_LEVELS:
            raise ValueError("unsupported toxicity level")
        return value


class EntityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: str
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("type")
    @classmethod
    def validate_entity_type(cls, value):
        if value not in ENTITY_TYPES:
            raise ValueError("unsupported entity type")
        return value


class MarketOrSocialSignalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_type: str
    strength: str
    rationale: str

    @field_validator("signal_type")
    @classmethod
    def validate_signal_type(cls, value):
        if value not in SIGNAL_TYPES:
            raise ValueError("unsupported signal type")
        return value

    @field_validator("strength")
    @classmethod
    def validate_strength(cls, value):
        if value not in SIGNAL_STRENGTHS:
            raise ValueError("unsupported signal strength")
        return value


class AiEnrichmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sentiment: str
    topics: list[str]
    entities: list[EntityModel]
    summary: str
    toxicity_risk: ToxicityRiskModel
    intent: str
    market_or_social_signal: MarketOrSocialSignalModel

    @field_validator("sentiment")
    @classmethod
    def validate_sentiment(cls, value):
        if value not in SENTIMENTS:
            raise ValueError("unsupported sentiment")
        return value

    @field_validator("intent")
    @classmethod
    def validate_intent(cls, value):
        if value not in INTENTS:
            raise ValueError("unsupported intent")
        return value


class BaseEnrichmentProvider(ABC):
    provider_name = LOCAL_PROVIDER
    default_model = LOCAL_ENRICHER_MODEL
    requires_api_key = False

    def __init__(self, model=None, api_key=None, base_url=None):
        self.model = model or self.default_model
        self.api_key = api_key
        self.base_url = base_url

    @property
    def enrichment_mode(self):
        return "local"

    def is_configured(self):
        return bool(self.api_key) if self.requires_api_key else True

    @abstractmethod
    def enrich(self, row):
        raise NotImplementedError


class LocalRuleProvider(BaseEnrichmentProvider):
    provider_name = LOCAL_PROVIDER
    default_model = LOCAL_ENRICHER_MODEL

    def enrich(self, row):
        return _local_ai_enrichment(row["text"])


class OpenAICompatibleProvider(BaseEnrichmentProvider):
    provider_name = "openai_compatible"
    default_model = "gpt-4.1-mini"
    requires_api_key = True

    @property
    def enrichment_mode(self):
        return "local_llm" if self.provider_name in LOCAL_LLM_PROVIDERS else "api"

    def is_configured(self):
        if self.provider_name in LOCAL_LLM_PROVIDERS:
            return bool(self.base_url)
        return bool(self.api_key)

    def enrich(self, row):
        from openai import OpenAI

        client_kwargs = {}
        if self.api_key:
            client_kwargs["api_key"] = self.api_key
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        client = OpenAI(**client_kwargs)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only a JSON object with these keys: sentiment, topics, "
                        "entities, summary, toxicity_risk, intent, market_or_social_signal. "
                        "Do not invent tweet IDs, source URLs, authors, metrics, or market "
                        "signals. Use signal_type 'none' when the tweet does not support one."
                    ),
                },
                {"role": "user", "content": json.dumps(_tweet_payload(row), ensure_ascii=False)},
            ],
            response_format={"type": "json_object"},
            temperature=0,
        )
        return json.loads(response.choices[0].message.content)


class AnthropicProvider(BaseEnrichmentProvider):
    provider_name = "anthropic"
    default_model = "claude-3-5-haiku-latest"
    requires_api_key = True

    @property
    def enrichment_mode(self):
        return "api"

    def enrich(self, row):
        import anthropic

        client = anthropic.Anthropic(api_key=self.api_key)
        response = client.messages.create(
            model=self.model,
            max_tokens=1200,
            temperature=0,
            system=(
                "Return only a JSON object with these keys: sentiment, topics, entities, "
                "summary, toxicity_risk, intent, market_or_social_signal. Do not invent "
                "source metadata or unsupported market signals."
            ),
            messages=[{"role": "user", "content": json.dumps(_tweet_payload(row), ensure_ascii=False)}],
        )
        text = "".join(block.text for block in response.content if getattr(block, "type", "") == "text")
        return json.loads(text)


class HuggingFaceProvider(OpenAICompatibleProvider):
    provider_name = "huggingface"
    default_model = "meta-llama/Llama-3.1-8B-Instruct"


class OllamaProvider(OpenAICompatibleProvider):
    provider_name = "ollama"
    default_model = "llama3.1"
    requires_api_key = False


class VllmProvider(OpenAICompatibleProvider):
    provider_name = "vllm"
    default_model = "local-model"
    requires_api_key = False


class LmStudioProvider(OpenAICompatibleProvider):
    provider_name = "lmstudio"
    default_model = "local-model"
    requires_api_key = False


class TogetherProvider(OpenAICompatibleProvider):
    provider_name = "together"
    default_model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"


class GroqProvider(OpenAICompatibleProvider):
    provider_name = "groq"
    default_model = "llama-3.1-8b-instant"


class FireworksProvider(OpenAICompatibleProvider):
    provider_name = "fireworks"
    default_model = "accounts/fireworks/models/llama-v3p1-8b-instruct"


PROVIDER_REGISTRY = {
    "local": LocalRuleProvider,
    "openai": OpenAICompatibleProvider,
    "openai_compatible": OpenAICompatibleProvider,
    "anthropic": AnthropicProvider,
    "huggingface": HuggingFaceProvider,
    "ollama": OllamaProvider,
    "vllm": VllmProvider,
    "lmstudio": LmStudioProvider,
    "together": TogetherProvider,
    "groq": GroqProvider,
    "fireworks": FireworksProvider,
}


def run_twitter_etl():
    rows = load_source_rows()
    normalized_rows = [_normalize_tweet(row) for row in rows]
    normalized_rows = [row for row in normalized_rows if row["text"]]
    enriched = enrich_tweets(normalized_rows)

    output_path = Path(os.getenv("OUTPUT_CSV_PATH", "refined_tweets.csv"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(_enriched_csv_projection(enriched)).to_csv(output_path, index=False)

    jsonl_path = Path(os.getenv("OUTPUT_JSONL_PATH", "outputs/enriched_tweets.jsonl"))
    json_path = Path(os.getenv("OUTPUT_JSON_PATH", "outputs/enriched_tweets.json"))
    write_enriched_outputs(enriched, jsonl_path=jsonl_path, json_path=json_path)

    return {
        "csv": str(output_path),
        "jsonl": str(jsonl_path),
        "json": str(json_path),
        "records": len(enriched),
    }


def enrich_tweets(normalized_rows):
    return [enrich_tweet(row) for row in normalized_rows]


def enrich_tweet(row):
    enrichment_result = _run_provider_enrichment(row)
    ai_enrichment = enrichment_result["ai_enrichment"]

    domain_analysis = _domain_analysis(row["text"], ai_enrichment)
    record = {
        "tweet": _tweet_payload(row),
        "ai_enrichment": ai_enrichment,
        "domain_analysis": domain_analysis,
        "quality": {
            "schema_version": SCHEMA_VERSION,
            "ai_provider": enrichment_result["ai_provider"],
            "ai_model": enrichment_result["ai_model"],
            "enrichment_mode": enrichment_result["enrichment_mode"],
            "fallback_used": enrichment_result["fallback_used"],
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
    _write_enriched_outputs(records, jsonl_path, json_path, schema_version=SCHEMA_VERSION)


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
    if quality.get("ai_provider") and quality.get("ai_provider") not in SUPPORTED_AI_PROVIDERS:
        errors.append("quality.ai_provider is invalid")
    if quality.get("enrichment_mode") and quality.get("enrichment_mode") not in ENRICHMENT_MODES:
        errors.append("quality.enrichment_mode is invalid")
    if "fallback_used" in quality and not isinstance(quality.get("fallback_used"), bool):
        errors.append("quality.fallback_used must be boolean")
    return errors


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


def _run_provider_enrichment(row):
    requested_mode = _enrichment_mode_from_env()
    provider = _provider_from_env()
    if requested_mode == "local":
        provider = LocalRuleProvider()
    provider_errors = []
    if provider.is_configured():
        try:
            ai_enrichment = _provider_ai_enrichment(row, provider, requested_mode)
            return {
                "ai_enrichment": ai_enrichment,
                "ai_provider": provider.provider_name,
                "ai_model": provider.model,
                "enrichment_mode": _quality_enrichment_mode(provider, requested_mode),
                "fallback_used": False,
                "provider_errors": [],
            }
        except Exception as exc:
            provider_errors.append(str(exc))
    elif provider.provider_name != LOCAL_PROVIDER:
        provider_errors.append(f"{provider.provider_name} provider is not configured")

    fallback = LocalRuleProvider()
    return {
        "ai_enrichment": fallback.enrich(row),
        "ai_provider": fallback.provider_name,
        "ai_model": fallback.model,
        "enrichment_mode": "local",
        "fallback_used": provider.provider_name != LOCAL_PROVIDER,
        "provider_errors": provider_errors,
    }


def _provider_ai_enrichment(row, provider, requested_mode):
    if provider.provider_name == LOCAL_PROVIDER:
        return provider.enrich(row)
    model_enrichment = _validate_ai_enrichment(provider.enrich(row))
    if requested_mode != "hybrid":
        return model_enrichment
    local_enrichment = LocalRuleProvider().enrich(row)
    merged = dict(local_enrichment)
    merged.update(model_enrichment)
    return _validate_ai_enrichment(merged)


def _quality_enrichment_mode(provider, requested_mode):
    if provider.provider_name == LOCAL_PROVIDER:
        return "local"
    if requested_mode == "hybrid":
        return "hybrid"
    return provider.enrichment_mode


def _enrichment_mode_from_env():
    mode = os.getenv("AI_ENRICHMENT_MODE", "auto").strip().lower()
    if mode in ENRICHMENT_MODES:
        return mode
    return "auto"


def _provider_from_env():
    provider_name = os.getenv("AI_PROVIDER", LOCAL_PROVIDER).strip().lower() or LOCAL_PROVIDER
    provider_name = _legacy_provider_name(provider_name)
    provider_cls = PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        provider_cls = LocalRuleProvider
    provider = provider_cls(
        model=_provider_model(provider_name, provider_cls),
        api_key=_provider_api_key(provider_name),
        base_url=_provider_base_url(provider_name),
    )
    if provider_name == "openai":
        provider.provider_name = "openai"
    return provider


def _legacy_provider_name(provider_name):
    aliases = {"local_llm": "ollama", "openai-compatible": "openai_compatible"}
    return aliases.get(provider_name, provider_name)


def _provider_model(provider_name, provider_cls):
    legacy_model = os.getenv("OPENAI_MODEL") if provider_name == "openai" else None
    return os.getenv("AI_MODEL") or legacy_model or provider_cls.default_model


def _provider_api_key(provider_name):
    provider_env = f"{provider_name.upper()}_API_KEY"
    if provider_name == "openai":
        return os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
    if provider_name == "anthropic":
        return os.getenv("AI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    return os.getenv("AI_API_KEY") or os.getenv(provider_env)


def _provider_base_url(provider_name):
    provider_env = f"{provider_name.upper()}_BASE_URL"
    defaults = {
        "ollama": "http://localhost:11434/v1",
        "lmstudio": "http://localhost:1234/v1",
        "vllm": "http://localhost:8000/v1",
    }
    return os.getenv("AI_BASE_URL") or os.getenv(provider_env) or defaults.get(provider_name)


def _validate_ai_enrichment(payload):
    if not isinstance(payload, dict):
        raise ValueError("AI provider returned a non-object payload")
    model = AiEnrichmentModel.model_validate(payload)
    return model.model_dump()


def _try_openai_enrichment(row):
    """Backward-compatible helper retained for older callers."""
    try:
        provider = OpenAICompatibleProvider(
            model=os.getenv("AI_MODEL") or os.getenv("OPENAI_MODEL"),
            api_key=os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("AI_BASE_URL"),
        )
        return _validate_ai_enrichment(provider.enrich(row))
    except (Exception, ValidationError):
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


def _require(data, key, errors):
    if data.get(key) in (None, ""):
        errors.append(f"{key} is required")


def _validate_score(value, path, errors):
    if not isinstance(value, (int, float)) or value < 0 or value > 1:
        errors.append(f"{path} must be between 0 and 1")
