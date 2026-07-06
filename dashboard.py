"""
Streamlit analytics dashboard for the Twitter data pipeline.

Usage:
    streamlit run dashboard.py

Reads enriched JSONL first, then falls back to refined_tweets.csv. Renders
analytics charts and refreshes every 5 minutes via st.cache_data.
"""
from __future__ import annotations

import ast
import json
import os
from collections import Counter

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Twitter Pipeline Dashboard",
    page_icon=":bird:",
    layout="wide",
)

st.title("X / Twitter Data Pipeline — Live Analytics")
st.caption("Powered by Apache Airflow · Model-agnostic AI enrichment · DuckDB")

# ---------------------------------------------------------------------------
# Data loading (cached 5 min)
# ---------------------------------------------------------------------------
JSONL_PATH = os.environ.get("TWEET_JSONL_PATH", os.environ.get("OUTPUT_JSONL_PATH", "outputs/enriched_tweets.jsonl"))
CSV_PATH = os.environ.get("TWEET_CSV_PATH", os.environ.get("OUTPUT_CSV_PATH", "outputs/refined_tweets.csv"))


@st.cache_data(ttl=300)
def load_data(jsonl_path: str, csv_path: str) -> pd.DataFrame:
    if os.path.exists(jsonl_path):
        records = []
        with open(jsonl_path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    records.append(_flatten_enriched_record(json.loads(line)))
        return pd.DataFrame(records)
    if not os.path.exists(csv_path):
        return pd.DataFrame()
    con = duckdb.connect()
    df = con.execute(f"SELECT * FROM read_csv_auto('{csv_path}')").df()
    df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
    return df


def _flatten_enriched_record(record: dict) -> dict:
    tweet = record["tweet"]
    ai = record["ai_enrichment"]
    domain = record["domain_analysis"]
    quality = record["quality"]
    signal = ai["market_or_social_signal"]
    return {
        "user": tweet["author_handle"],
        "text": tweet["text"],
        "favorite_count": tweet["metrics"]["likes"],
        "retweet_count": tweet["metrics"]["retweets"],
        "created_at": pd.to_datetime(tweet["created_at"], errors="coerce"),
        "sentiment": ai["sentiment"],
        "topics": ai["topics"],
        "summary": ai["summary"],
        "intent": ai["intent"],
        "signal_type": signal["signal_type"],
        "primary_domain": domain["primary_domain"],
        "source_confidence": tweet["source_confidence"],
        "requires_human_review": quality["requires_human_review"],
    }


df = load_data(JSONL_PATH, CSV_PATH)

if df.empty:
    st.warning(
        f"No data found at **{JSONL_PATH}** or **{CSV_PATH}**.  "
        "Run the Airflow pipeline first, then refresh this page."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Top-level KPIs
# ---------------------------------------------------------------------------
st.subheader("Overview")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Tweets", f"{len(df):,}")
col2.metric("Avg Likes", f"{df['favorite_count'].mean():,.0f}")
col3.metric("Avg Retweets", f"{df['retweet_count'].mean():,.0f}")
col4.metric(
    "Most Active Day",
    str(df.set_index("created_at")["text"].resample("D").count().idxmax().date())
    if not df["created_at"].isna().all()
    else "N/A",
)

st.divider()

# ---------------------------------------------------------------------------
# Sentiment distribution (LLM-enriched)
# ---------------------------------------------------------------------------
left, right = st.columns(2)

with left:
    st.subheader("Sentiment Distribution")
    if "sentiment" in df.columns and df["sentiment"].notna().any():
        fig_sentiment = px.pie(
            df.dropna(subset=["sentiment"]),
            names="sentiment",
            color="sentiment",
            color_discrete_map={
                "positive": "#2ecc71",
                "negative": "#e74c3c",
                "neutral": "#95a5a6",
            },
            hole=0.4,
        )
        fig_sentiment.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_sentiment, use_container_width=True)
    else:
        st.info("No sentiment data — LLM enrichment has not run yet.")

# ---------------------------------------------------------------------------
# Top topics (LLM-enriched)
# ---------------------------------------------------------------------------
with right:
    st.subheader("Top Topics")
    if "topics" in df.columns and df["topics"].notna().any():
        all_topics: list[str] = []
        for raw in df["topics"].dropna():
            try:
                parsed = json.loads(raw) if isinstance(raw, str) else raw
                if isinstance(parsed, list):
                    all_topics.extend(parsed)
            except (json.JSONDecodeError, TypeError):
                try:
                    all_topics.extend(ast.literal_eval(raw))
                except Exception:
                    pass

        if all_topics:
            topic_df = pd.DataFrame(
                Counter(all_topics).most_common(10), columns=["Topic", "Count"]
            )
            fig_topics = px.bar(
                topic_df, x="Count", y="Topic", orientation="h",
                color="Count", color_continuous_scale="Blues",
            )
            fig_topics.update_layout(yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_topics, use_container_width=True)
        else:
            st.info("No topic data available.")
    else:
        st.info("No topic data — LLM enrichment has not run yet.")

st.divider()

# ---------------------------------------------------------------------------
# Engagement over time
# ---------------------------------------------------------------------------
st.subheader("Engagement Over Time")

if not df["created_at"].isna().all():
    ts = (
        df.set_index("created_at")
        .resample("D")[["favorite_count", "retweet_count"]]
        .sum()
        .reset_index()
    )
    fig_ts = px.line(
        ts, x="created_at", y=["favorite_count", "retweet_count"],
        labels={"value": "Count", "created_at": "Date", "variable": "Metric"},
        color_discrete_map={"favorite_count": "#3498db", "retweet_count": "#e67e22"},
    )
    st.plotly_chart(fig_ts, use_container_width=True)
else:
    st.info("No timestamp data available for the timeline chart.")

st.divider()

# ---------------------------------------------------------------------------
# Raw data explorer
# ---------------------------------------------------------------------------
st.subheader("Raw Tweet Explorer")

display_cols = [
    c
    for c in [
        "user",
        "text",
        "favorite_count",
        "retweet_count",
        "sentiment",
        "primary_domain",
        "signal_type",
        "summary",
        "created_at",
    ]
    if c in df.columns
]
st.dataframe(df[display_cols].head(50), use_container_width=True)
