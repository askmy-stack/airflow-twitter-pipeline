# Project Status — X/Twitter Data Pipeline

## What This Project Does

An automated daily pipeline that:
1. **Fetches** tweets from a Twitter user via Twitter API v2
2. **Enriches** each tweet using Claude AI (sentiment, topics, summary)
3. **Validates** the data schema before saving
4. **Saves** results to S3 (or local CSV as fallback)
5. **Visualises** results on a live Streamlit dashboard

---

## What Has Been Done

### 1. Bug Fixes
- Fixed a critical authentication bug where Twitter API keys were passed in the wrong order
- Removed a variable named `list` that was overwriting Python's built-in

### 2. API Modernisation
- Migrated from the deprecated Twitter API v1.1 to **Twitter API v2**
- Updated Airflow DAG from the old 1.x style to the modern **Airflow 2.x TaskFlow API**

### 3. Hero Feature 1 — AI/LLM Enrichment (`twitter_etl.py`)
- Every tweet is sent to the **Claude API** which returns:
  - `sentiment` → positive / negative / neutral
  - `topics` → up to 3 topic tags
  - `summary` → one-sentence description
- If the API call fails for a tweet, it is skipped gracefully (does not crash the pipeline)

### 4. Hero Feature 2 — Real-Time Kafka Streaming (`streaming/twitter_stream.py`)
- Connects to the **Twitter v2 Filtered Stream** (live feed, not polling)
- Publishes each tweet as a JSON message to a **Kafka topic**
- Useful for near-real-time downstream processing

### 5. Hero Feature 3 — CI/CD Pipeline (`.github/workflows/pipeline.yml`)
- Automatically runs on every code push via **GitHub Actions**
- Three quality gates in order:
  1. **Ruff** — code linting
  2. **mypy** — static type checking
  3. **pytest** — 10 unit tests (all external APIs are mocked, no real credentials needed)

### 6. Production Readiness
| What | How |
|---|---|
| Schema validation | Pandera checks column types and value ranges before every save |
| Cloud storage | Writes to S3 with date partitioning (`year=/month=/day=`) |
| Secrets management | All credentials come from environment variables, never hardcoded |
| Local dev stack | `docker-compose.yml` starts everything with one command |
| Credential template | `.env.example` lists every variable needed |
| Git hygiene | `.gitignore` excludes secrets, CSV output, and runtime files |

### 7. Analytics Dashboard (`dashboard.py`)
- Built with **Streamlit + Plotly + DuckDB**
- Shows: tweet count, avg likes/retweets, sentiment pie chart, top topics bar chart, engagement timeline

### 8. Documentation
- `CLAUDE.md` — full codebase guide for AI assistants and developers
- `PROJECT_STATUS.md` — this file

---

## Repository Structure (Current State)

```
├── twitter_dag.py                  # Airflow DAG (orchestration)
├── twitter_etl.py                  # Extract → Enrich → Validate → Load
├── dashboard.py                    # Streamlit analytics UI
├── requirements.txt                # All Python dependencies
├── docker-compose.yml              # Local dev stack
├── .env.example                    # Credential template
├── .gitignore
├── .github/
│   └── workflows/pipeline.yml      # GitHub Actions CI
├── streaming/
│   └── twitter_stream.py           # Kafka real-time producer
├── tests/
│   └── test_twitter_etl.py         # 10 unit tests
└── CLAUDE.md
```

---

## What Still Needs to Be Done

### Step 1 — Get API Credentials

You need accounts and keys for three services:

| Service | Where to get it | Variables needed |
|---|---|---|
| Twitter / X | developer.twitter.com → Project → App | `TWITTER_BEARER_TOKEN`, `TWITTER_CONSUMER_KEY`, `TWITTER_CONSUMER_SECRET`, `TWITTER_ACCESS_TOKEN`, `TWITTER_ACCESS_SECRET` |
| Anthropic (Claude) | console.anthropic.com → API Keys | `ANTHROPIC_API_KEY` |
| AWS S3 *(optional)* | AWS Console → IAM → Create user | `S3_BUCKET`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |

> **Twitter API note:** The v2 `get_users_tweets` endpoint requires at minimum a **Basic tier** ($100/mo). The free tier only supports posting tweets. If you don't have access, the pipeline code is correct and ready — you just need the tier upgrade.

---

### Step 2 — Configure Credentials Locally

```bash
# Copy the template
cp .env.example .env

# Open .env and fill in every value
nano .env
```

---

### Step 3 — Run Locally with Docker (Recommended)

```bash
# Start Airflow + Postgres + Kafka + Zookeeper + Streamlit
docker compose up -d

# First-time only: wait ~60 seconds for services to initialise, then check
docker compose ps        # all services should show "healthy" or "running"
```

- Airflow UI → http://localhost:8080  (login: `admin` / `admin`)
- Streamlit dashboard → http://localhost:8501

---

### Step 4 — Configure Airflow

1. Open the Airflow UI at http://localhost:8080
2. Go to **Admin → Variables → Add**
   - Key: `twitter_target_user`
   - Value: `elonmusk` (or any valid Twitter username)
3. Go to **Admin → Connections** and add your AWS connection if using S3

---

### Step 5 — Run the Pipeline

**Option A — Airflow UI (recommended)**
1. Navigate to **DAGs** in the Airflow UI
2. Find `twitter_pipeline`
3. Toggle it **On**
4. Click the ▶ play button → **Trigger DAG**
5. Watch each task turn green: `extract` → `enrich` → `load`

**Option B — Command line**
```bash
docker exec -it <airflow-scheduler-container> airflow dags trigger twitter_pipeline
```

---

### Step 6 — View the Dashboard

Once the pipeline completes and `refined_tweets.csv` is written:

```bash
# If running outside Docker
pip install streamlit plotly duckdb
streamlit run dashboard.py
```

Or open http://localhost:8501 if Docker is running.

---

### Step 7 — Run the Kafka Stream (Optional)

```bash
# Make sure Kafka is running (included in docker-compose.yml)
# Then in a separate terminal:
pip install kafka-python tweepy
python -m streaming.twitter_stream "#AI" "#SpaceX" "Elon Musk"
```

Each matching tweet will be published to the `raw_tweets` Kafka topic in real time.

---

### Step 8 — Deploy to Production (Cloud)

For a production deployment, the recommended path is:

```
Local dev  →  MWAA (Managed Airflow on AWS)  →  S3  →  Athena / QuickSight
```

Steps:
1. **Package the DAG** — upload `twitter_dag.py` and `twitter_etl.py` to the S3 DAGs bucket configured in MWAA
2. **Set environment variables** — add secrets via AWS Secrets Manager, referenced in MWAA's environment config
3. **Set Airflow Variable** — `twitter_target_user` via the MWAA UI
4. **Enable the DAG** — it will run daily automatically
5. **Output** — tweets land in S3 under `s3://your-bucket/tweets/year=.../month=.../day=.../`

Alternatively, deploy on any VPS (EC2, GCP VM, DigitalOcean):
```bash
pip install apache-airflow
airflow db migrate
airflow users create --username admin --password admin --role Admin --firstname A --lastname B --email a@b.com
airflow webserver &
airflow scheduler &
```

---

## Quick Reference — Run Everything Locally

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd X-Twitter-Data-Pipeline-using-Apache-Airflow

# 2. Add credentials
cp .env.example .env && nano .env

# 3. Start all services
docker compose up -d

# 4. Open Airflow, enable and trigger the DAG
open http://localhost:8080

# 5. Open the dashboard after the DAG completes
open http://localhost:8501
```

---

## Remaining Gaps Summary

| Item | Effort | Blocker |
|---|---|---|
| Twitter API Basic tier | Low | Requires paid subscription ($100/mo) |
| Fill `.env` credentials | Low | Need developer accounts (Twitter, Anthropic) |
| AWS S3 bucket + IAM | Medium | Optional — local CSV works without it |
| Production deployment (MWAA/EC2) | Medium | Requires cloud account |
| Kafka consumer DAG | Medium | Streaming producer is done; consumer not yet written |
| DuckDB aggregation layer | Low | Dashboard works without it; adds query performance |
