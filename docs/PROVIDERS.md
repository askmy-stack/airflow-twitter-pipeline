# AI Provider Guide

Social Signal Pipeline uses `AI_PROVIDER`, `AI_ENRICHMENT_MODE`, `AI_MODEL`, `AI_API_KEY`, and `AI_BASE_URL` to select an enrichment backend.

Every provider response is validated against the enrichment schema. Invalid output falls back to local deterministic enrichment.

## Local Rules

```bash
export AI_PROVIDER=local
export AI_ENRICHMENT_MODE=local
export AI_MODEL=local-rule-enricher-v1
```

Use this for tests, demos, and no-credential development.

## Ollama

```bash
ollama serve
ollama pull llama3.1

export AI_PROVIDER=ollama
export AI_ENRICHMENT_MODE=local_llm
export AI_MODEL=llama3.1
export AI_BASE_URL=http://localhost:11434/v1
```

## vLLM

```bash
export AI_PROVIDER=vllm
export AI_ENRICHMENT_MODE=local_llm
export AI_MODEL=local-model
export AI_BASE_URL=http://localhost:8000/v1
```

## LM Studio

```bash
export AI_PROVIDER=lmstudio
export AI_ENRICHMENT_MODE=local_llm
export AI_MODEL=local-model
export AI_BASE_URL=http://localhost:1234/v1
```

## OpenAI-Compatible Hosted APIs

```bash
export AI_PROVIDER=openai_compatible
export AI_ENRICHMENT_MODE=api
export AI_MODEL=provider/model-name
export AI_API_KEY=...
export AI_BASE_URL=https://api.provider.example/v1
```

This pattern can support compatible hosted providers such as Together, Groq, Fireworks, and other OpenAI-compatible endpoints.

## Named Hosted Providers

```bash
export AI_PROVIDER=together
export AI_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo
export AI_API_KEY=...
```

```bash
export AI_PROVIDER=groq
export AI_MODEL=llama-3.1-8b-instant
export AI_API_KEY=...
```

```bash
export AI_PROVIDER=fireworks
export AI_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct
export AI_API_KEY=...
```

## Anthropic

```bash
export AI_PROVIDER=anthropic
export AI_MODEL=claude-3-5-haiku-latest
export AI_API_KEY=...
```

## Safety Expectations

- Providers may only return enrichment fields.
- Providers must not control tweet IDs, URLs, author handles, metrics, connector names, or source confidence.
- Unsupported market/social claims must use `signal_type: none`.
- Failed provider calls must fall back to local enrichment.
