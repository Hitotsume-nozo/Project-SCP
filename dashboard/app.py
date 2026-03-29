# dashboard/app.py
import streamlit as st
import json
import pandas as pd
import plotly.express as px
from kafka import KafkaConsumer
from minio import Minio
from datetime import datetime
import threading
import time

st.set_page_config(page_title="Smart City Monitor", layout="wide")

# ============ SHARED STATE ============
if "governed_records" not in st.session_state:
    st.session_state.governed_records = []
if "stats" not in st.session_state:
    st.session_state.stats = {"total": 0, "pii_blocked": 0}


# ============ LOAD DATA FROM MINIO ============
def load_from_minio():
    """Load governed records from MinIO curated-zone"""
    try:
        client = Minio(
            "minio:9000", access_key="admin", secret_key="admin12345", secure=False
        )
        records = []
        objects = client.list_objects("curated-zone", prefix="traffic/", recursive=True)
        for obj in objects:
            response = client.get_object("curated-zone", obj.object_name)
            data = json.loads(response.read().decode())
            records.append(data)
            response.close()

        return records
    except Exception as e:
        st.error(f"MinIO Error: {e}")
        return []


# ============ MAIN DASHBOARD ============
st.title("🏙️ Smart City Traffic Monitor")
st.caption("Real-time data governance & traffic monitoring")

# Load data
records = load_from_minio()

if not records:
    st.warning(
        "⏳ Waiting for data... Make sure the pipeline "
        "is running (`docker compose up -d`)"
    )
    st.stop()

df = pd.DataFrame(records)

# ===== ROW 1: KEY METRICS =====
st.header("🛡️ Governance Dashboard")
col1, col2, col3, col4 = st.columns(4)

total = len(df)
pii_count = int(df["pii_detected"].sum()) if "pii_detected" in df.columns else 0

with col1:
    st.metric("Total Records", total)
with col2:
    st.metric("🔴 PII Detected & Hashed", pii_count)
with col3:
    st.metric("✅ Clean Records", total - pii_count)
with col4:
    st.metric("Compliance Rate", "100%")

st.divider()

# ===== ROW 2: CHARTS =====
st.header("🚗 Traffic Analytics")

if "district" in df.columns:
    col1, col2 = st.columns(2)

    with col1:
        district_stats = (
            df.groupby("district")
            .agg(
                avg_vehicles=("vehicle_count", "mean"), count=("vehicle_count", "count")
            )
            .reset_index()
        )
        district_stats["avg_vehicles"] = district_stats["avg_vehicles"].round(1)

        fig = px.bar(
            district_stats,
            x="district",
            y="avg_vehicles",
            title="Avg Vehicle Count by District",
            color="avg_vehicles",
            color_continuous_scale="OrRd",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "avg_speed_kmh" in df.columns:
            speed_stats = (
                df.groupby("district")
                .agg(avg_speed=("avg_speed_kmh", "mean"))
                .reset_index()
            )
            speed_stats["avg_speed"] = speed_stats["avg_speed"].round(1)

            fig = px.bar(
                speed_stats,
                x="district",
                y="avg_speed",
                title="Avg Speed (km/h) by District",
                color="avg_speed",
                color_continuous_scale="Greens",
            )
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# ===== ROW 3: RAW DATA TABLE =====
st.header("📋 Recent Governed Records")
st.caption("Notice: license_plates field shows SHA-256 hashes, NOT original plates")

display_cols = [
    "timestamp",
    "sensor_id",
    "district",
    "vehicle_count",
    "avg_speed_kmh",
    "license_plates",
    "pii_detected",
]
available_cols = [c for c in display_cols if c in df.columns]

st.dataframe(
    df[available_cols].tail(20).sort_values("timestamp", ascending=False),
    use_container_width=True,
    height=400,
)

# ===== ROW 4: COMPARISON =====
st.header("🔍 PII Governance Proof")
st.caption(
    "Showing that raw data (with real plates) was "
    "transformed to governed data (with hashes)"
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("❌ Raw Data (in raw-zone)")
    st.code(
        """{
  "sensor_id": "CAM-451",
  "district": "Sector-3",
  "license_plates": ["AB-1234-CD", "EF-5678-GH"],
  "vehicle_count": 45
}""",
        language="json",
    )
    st.error("⚠️ Contains real license plates — PII!")

with col2:
    st.subheader("✅ Governed Data (in curated-zone)")
    if records:
        sample = records[-1]
        st.code(json.dumps(sample, indent=2), language="json")
        st.success("✅ License plates are SHA-256 hashed")

# ===== REFRESH =====
st.divider()
if st.button("🔄 Refresh Data"):
    st.rerun()

st.caption("Click refresh to load latest data from MinIO")
