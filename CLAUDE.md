# CLAUDE.md — X/Twitter Data Pipeline using Apache Airflow

## Project Overview

This is an educational Apache Airflow ETL pipeline that fetches tweets from a Twitter user's timeline via the Twitter API v1.1 (using Tweepy), transforms the data, and saves it as a CSV file. The project demonstrates how to integrate Airflow with external APIs for scheduled data extraction.

## Repository Structure

```
X-Twitter-Data-Pipeline-using-Apache-Airflow/
├── CLAUDE.md               # This file — AI assistant guidance
├── README.md               # Minimal project title only
├── twitter_dag.py          # Airflow DAG definition and scheduling
├── twitter_etl.py          # ETL logic: extract, transform, load tweets
└── twitter_commands.sh     # System/pip install commands for dependencies
```

## File Responsibilities

### `twitter_dag.py`
- Defines the Airflow DAG (`twitter_dag`) with a daily schedule (`timedelta(days=1)`)
- Single task: `complete_twitter_etl` (PythonOperator) calls `run_twitter_etl()`
- Start date: `datetime(2020, 11, 8)`; 1 retry with 1-minute delay
- Uses pre-Airflow-2.0 import path: `airflow.operators.python_operator`

### `twitter_etl.py`
- Contains the single function `run_twitter_etl()` — the full ETL in one callable
- **Extract**: Authenticates with Twitter OAuth, fetches up to 200 tweets from `@elonmusk` (excludes retweets, uses `extended` mode for full text)
- **Transform**: Builds a list of dicts with fields: `user`, `text`, `favorite_count`, `retweet_count`, `created_at`
- **Load**: Writes a Pandas DataFrame to `refined_tweets.csv` in the working directory

### `twitter_commands.sh`
- Shell commands (not a runnable script with shebang) for manual environment setup
- Installs: `apache-airflow`, `pandas`, `s3fs`, `tweepy` via pip

## Development Setup

### Prerequisites
- Python 3
- pip
- An Apache Airflow installation
- Twitter API v1.1 developer credentials (OAuth 1.0a)

### Installation
Run the commands from `twitter_commands.sh` manually:
```bash
sudo apt-get update
sudo apt install python3-pip
sudo pip install apache-airflow pandas s3fs tweepy
```

### Configuration (Required Before Running)
Fill in the four credential placeholders in `twitter_etl.py:9-12`:
```python
access_key = ""       # Twitter Access Token
access_secret = ""    # Twitter Access Token Secret
consumer_key = ""     # Twitter API Key (App)
consumer_secret = ""  # Twitter API Secret (App)
```
**Never commit real credentials.** Use environment variables or Airflow Connections instead.

### Running the DAG
1. Place `twitter_dag.py` and `twitter_etl.py` in the Airflow `dags/` folder
2. Start Airflow scheduler and webserver
3. Enable `twitter_dag` in the Airflow UI
4. The DAG runs daily; trigger manually for immediate execution

## Code Conventions

- **Language**: Python 3, snake_case for all file and function names
- **Style**: PEP 8 naming; minimal inline comments; imports grouped at top
- **ETL pattern**: Single function `run_twitter_etl()` encapsulates the full pipeline
- **DAG pattern**: One DAG, one PythonOperator task, no inter-task dependencies
- **Output**: CSV file (`refined_tweets.csv`) written to the current working directory

## Known Limitations and Issues

| Issue | Location | Notes |
|---|---|---|
| Hardcoded empty credentials | `twitter_etl.py:9-12` | Must be filled before use |
| Hardcoded target user (`@elonmusk`) | `twitter_etl.py:21` | Not parameterized |
| Deprecated import path | `twitter_dag.py:3` | Use `airflow.operators.python` in Airflow 2.x |
| `tweepy.OAuthHandler` arg order bug | `twitter_etl.py:16-17` | `access_key`/`access_secret` passed to `OAuthHandler` (should be `consumer_key`/`consumer_secret`); `set_access_token` args are reversed too |
| No error handling | `twitter_etl.py` | No try/except; API failures crash silently |
| No logging | both files | No Airflow or standard library logging |
| `s3fs` imported but unused | `twitter_etl.py:5` | S3 upload not implemented |
| Variable named `list` shadows builtin | `twitter_etl.py:30` | Rename to `tweet_list` or similar |
| No tests | entire repo | No test files or test framework configured |

## When Making Changes

- **Fixing credentials**: Use Airflow Variables or environment variables — do not hardcode secrets
- **Upgrading to Airflow 2.x**: Change `from airflow.operators.python_operator import PythonOperator` to `from airflow.operators.python import PythonOperator`
- **Fixing the Tweepy auth bug**: `OAuthHandler` takes `consumer_key, consumer_secret`; `set_access_token` takes `access_key, access_secret`
- **Adding error handling**: Wrap API calls and file I/O in try/except blocks; use `logging` or Airflow's task logger
- **Parameterizing the target user**: Pass `screen_name` as a DAG param or Airflow Variable rather than hardcoding
- **Implementing S3 upload**: Replace `df.to_csv('refined_tweets.csv')` with an S3 write using `s3fs` or an Airflow S3Hook

## Branch Strategy

- `main`: stable base
- Feature/documentation branches follow the pattern `claude/<description>-<id>`

## Dependencies Summary

| Package | Purpose |
|---|---|
| `apache-airflow` | Workflow orchestration and DAG scheduling |
| `tweepy` | Twitter API v1.1 client |
| `pandas` | DataFrame construction and CSV export |
| `s3fs` | AWS S3 filesystem interface (imported, not yet used) |
