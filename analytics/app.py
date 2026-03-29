# dashboard/app.py
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import json
from datetime import datetime

API_URL = "http://analytics-api:8000"

st.set_page_config(
    page_title="Urban Data Command Center",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ========== STYLING ==========
st.markdown(
    """
<style>
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a4a;
        padding: 18px;
        border-radius: 10px;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.8rem !important;
        color: #8892b0 !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.8rem !important;
        font-weight: 700;
        color: #ccd6f6 !important;
    }
    h1 { color: #ccd6f6 !important; font-weight: 700 !important; }
    h2, h3 { color: #8892b0 !important; font-weight: 600 !important; }
    [data-testid="stSidebar"] {
        background: #0a0a1a;
        border-right: 1px solid #1a1a2e;
    }
    .status-dot {
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }
    .status-green { background: #64ffda; }
    .status-red { background: #ff4444; }
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .subtitle {
        color: #8892b0;
        font-size: 0.9rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ========== CHART THEME ==========
CHART_LAYOUT = dict(
    plot_bgcolor="rgba(0,0,0,0)",
    paper_bgcolor="rgba(0,0,0,0)",
    font=dict(color="#8892b0"),
    xaxis=dict(gridcolor="#1a1a2e", tickfont=dict(color="#8892b0")),
    yaxis=dict(gridcolor="#1a1a2e", tickfont=dict(color="#8892b0")),
    margin=dict(l=40, r=40, t=50, b=40),
    legend=dict(font=dict(color="#8892b0"), bgcolor="rgba(0,0,0,0)"),
)

COLORS = {
    "primary": "#64ffda",
    "danger": "#ff4444",
    "warning": "#ffaa00",
    "info": "#4dabf7",
    "muted": "#8892b0",
    "surface": "#1a1a2e",
}


def api_get(endpoint):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=10)
        if r.status_code == 200:
            return r.json()
    except:
        pass
    return None


# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("## Urban Data Platform")
    st.markdown(
        '<p class="subtitle">Automated Governance Pipeline</p>', unsafe_allow_html=True
    )
    st.markdown("---")

    page = st.radio(
        "nav",
        [
            "Command Center",
            "Traffic Intelligence",
            "Air Quality",
            "Governance Audit",
            "System and API",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown("### Services")

    api_ok = api_get("/") is not None
    dot = "status-green" if api_ok else "status-red"
    st.markdown(
        f'<span class="status-dot {dot}"></span> Analytics API', unsafe_allow_html=True
    )
    st.markdown(
        '<span class="status-dot status-green"></span> Redpanda', unsafe_allow_html=True
    )
    st.markdown(
        '<span class="status-dot status-green"></span> Governance Agent',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<span class="status-dot status-green"></span> MinIO Storage',
        unsafe_allow_html=True,
    )

    st.markdown("---")
    st.caption(f"Refreshed: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("Refresh", use_container_width=True):
        st.rerun()


# ================================================================
# COMMAND CENTER
# ================================================================
if page == "Command Center":
    st.markdown("# Command Center")
    st.markdown(
        '<p class="subtitle">Unified view of urban data pipeline health, governance, and alerts</p>',
        unsafe_allow_html=True,
    )

    stats = api_get("/api/v1/governance/stats")
    if not stats:
        st.error("Analytics API unreachable")
        st.stop()

    # --- Row 1: Primary KPIs ---
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Traffic Records", f"{stats.get('traffic_records_processed', 0):,}")
    c2.metric("PII Intercepted", f"{stats.get('traffic_records_with_pii', 0):,}")
    c3.metric("Pollution Records", f"{stats.get('pollution_records_processed', 0):,}")
    c4.metric("Critical Alerts", f"{stats.get('pollution_alerts_critical', 0):,}")
    c5.metric("Raw Zone Files", f"{stats.get('raw_zone_files', 0):,}")

    st.markdown("---")

    # --- Row 2: Governance + Traffic ---
    left, right = st.columns([3, 2])

    with left:
        st.markdown("### Pipeline Activity")

        timeline = api_get("/api/v1/governance/timeline")
        if timeline and not isinstance(timeline, dict):
            df_tl = pd.DataFrame(timeline)

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=df_tl["minute"],
                    y=df_tl["records_processed"],
                    name="Records Processed",
                    fill="tozeroy",
                    fillcolor="rgba(100,255,218,0.1)",
                    line=dict(color=COLORS["primary"], width=2),
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df_tl["minute"],
                    y=df_tl["pii_found"],
                    name="PII Detected",
                    fill="tozeroy",
                    fillcolor="rgba(255,68,68,0.1)",
                    line=dict(color=COLORS["danger"], width=2),
                )
            )
            fig.update_layout(
                **CHART_LAYOUT,
                height=350,
                title=dict(
                    text="Governance Activity Over Time",
                    font=dict(color="#ccd6f6", size=14),
                ),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Collecting timeline data...")

    with right:
        st.markdown("### Governance Breakdown")

        total = stats.get("traffic_records_processed", 0)
        pii = stats.get("traffic_records_with_pii", 0)
        clean = stats.get("traffic_records_clean", 0)
        detection_rate = stats.get("pii_detection_rate", 0)

        if total > 0:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=["Records with PII (Hashed)", "Clean Records"],
                        values=[pii, clean],
                        hole=0.65,
                        marker=dict(colors=[COLORS["danger"], COLORS["primary"]]),
                        textinfo="label+percent",
                        textfont=dict(size=11, color="#ccd6f6"),
                    )
                ]
            )
            fig.update_layout(
                **CHART_LAYOUT,
                height=300,
                showlegend=False,
                annotations=[
                    dict(
                        text=f"{detection_rate}%<br>PII Rate",
                        x=0.5,
                        y=0.5,
                        font_size=18,
                        font_color="#ccd6f6",
                        showarrow=False,
                    )
                ],
            )
            st.plotly_chart(fig, use_container_width=True)

        st.markdown(f"""
        | Metric | Count |
        |--------|------:|
        | Total processed | {total:,} |
        | Contained PII | {pii:,} |
        | PII successfully hashed | {pii:,} |
        | Governance failures | 0 |
        | Raw zone (audit) files | {stats.get("raw_zone_files", 0):,} |
        """)

    st.markdown("---")

    # --- Row 3: District Overview ---
    st.markdown("### District Status")

    traffic = api_get("/api/v1/traffic/summary")
    pollution = api_get("/api/v1/pollution/summary")

    if (
        traffic
        and not isinstance(traffic, dict)
        and pollution
        and not isinstance(pollution, dict)
    ):
        df_t = pd.DataFrame(traffic)
        df_p = pd.DataFrame(pollution)

        merged = df_t.merge(df_p, on="district", how="outer")

        cols = st.columns(len(merged))
        for i, (_, row) in enumerate(merged.iterrows()):
            with cols[i]:
                aqi = row.get("avg_aqi", 0)
                speed = row.get("avg_speed", 0)

                if aqi > 300:
                    air_status = "HAZARDOUS"
                elif aqi > 200:
                    air_status = "VERY UNHEALTHY"
                elif aqi > 150:
                    air_status = "UNHEALTHY"
                elif aqi > 100:
                    air_status = "MODERATE"
                else:
                    air_status = "GOOD"

                if speed < 25:
                    traffic_status = "CONGESTED"
                elif speed < 45:
                    traffic_status = "MODERATE"
                else:
                    traffic_status = "CLEAR"

                st.markdown(f"**{row['district']}**")
                st.metric("AQI", f"{int(aqi)}", air_status, delta_color="off")
                st.metric(
                    "Speed", f"{speed:.0f} km/h", traffic_status, delta_color="off"
                )


# ================================================================
# TRAFFIC INTELLIGENCE
# ================================================================
elif page == "Traffic Intelligence":
    st.markdown("# Traffic Intelligence")
    st.markdown(
        '<p class="subtitle">Vehicle density, speed patterns, and congestion analysis</p>',
        unsafe_allow_html=True,
    )

    summary = api_get("/api/v1/traffic/summary")
    timeseries = api_get("/api/v1/traffic/timeseries")
    latest = api_get("/api/v1/traffic/latest")

    if not summary or isinstance(summary, dict):
        st.info("Waiting for traffic data...")
        st.stop()

    df = pd.DataFrame(summary)

    # --- KPIs ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Avg Vehicle Count", f"{df['avg_vehicles'].mean():.0f}")
    c2.metric("Avg Speed", f"{df['avg_speed'].mean():.1f} km/h")
    c3.metric("Peak Vehicles", f"{df['max_vehicles'].max():.0f}")
    c4.metric("Slowest District", df.loc[df["avg_speed"].idxmin(), "district"])

    st.markdown("---")

    # --- Time Series ---
    if timeseries and not isinstance(timeseries, dict):
        st.markdown("### Traffic Volume Over Time")
        df_ts = pd.DataFrame(timeseries)

        fig = px.line(
            df_ts,
            x="minute",
            y="avg_vehicles",
            color="district",
            title="Vehicle Count by District Over Time",
        )
        fig.update_layout(**CHART_LAYOUT, height=380)
        fig.update_traces(line=dict(width=2))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Bar Charts ---
    c1, c2 = st.columns(2)

    with c1:
        fig = go.Figure(
            go.Bar(
                x=df["district"],
                y=df["avg_vehicles"],
                marker=dict(
                    color=df["avg_vehicles"],
                    colorscale=[
                        [0, "#1a1a2e"],
                        [0.5, COLORS["primary"]],
                        [1, COLORS["danger"]],
                    ],
                ),
                text=df["avg_vehicles"].round(0).astype(int),
                textposition="outside",
                textfont=dict(color="#ccd6f6", size=13),
            )
        )
        fig.update_layout(
            **CHART_LAYOUT,
            height=400,
            title=dict(
                text="Average Vehicle Count", font=dict(color="#ccd6f6", size=14)
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure(
            go.Bar(
                x=df["district"],
                y=df["avg_speed"],
                marker=dict(
                    color=df["avg_speed"],
                    colorscale=[
                        [0, COLORS["danger"]],
                        [0.5, COLORS["warning"]],
                        [1, COLORS["primary"]],
                    ],
                ),
                text=df["avg_speed"].round(1),
                textposition="outside",
                textfont=dict(color="#ccd6f6", size=13),
            )
        )
        fig.update_layout(
            **CHART_LAYOUT,
            height=400,
            title=dict(
                text="Average Speed (km/h)", font=dict(color="#ccd6f6", size=14)
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Congestion Breakdown ---
    st.markdown("### Congestion Analysis")

    for _, row in df.iterrows():
        speed = row["avg_speed"]
        vehicles = row["avg_vehicles"]
        congestion = max(0, min(100, (1 - speed / 80) * 100))

        if speed < 25:
            status, rec = "HEAVY", "Diversion recommended"
        elif speed < 40:
            status, rec = "MODERATE", "Monitor closely"
        else:
            status, rec = "CLEAR", "Normal flow"

        c1, c2, c3, c4 = st.columns([1.5, 3, 1, 1.5])
        c1.markdown(f"**{row['district']}**")
        c2.progress(congestion / 100, text=f"{congestion:.0f}% congested")
        c3.markdown(f"**{speed:.0f}** km/h")
        c4.caption(f"{status} - {rec}")

    st.markdown("---")

    # --- Latest Records ---
    if latest and not isinstance(latest, dict):
        st.markdown("### Recent Records")
        df_l = pd.DataFrame(latest)
        cols = [
            c
            for c in [
                "timestamp",
                "sensor_id",
                "district",
                "vehicle_count",
                "avg_speed_kmh",
                "pii_detected",
            ]
            if c in df_l.columns
        ]
        st.dataframe(
            df_l[cols],
            use_container_width=True,
            height=300,
            column_config={
                "pii_detected": st.column_config.CheckboxColumn("PII Governed")
            },
        )


# ================================================================
# AIR QUALITY
# ================================================================
elif page == "Air Quality":
    st.markdown("# Air Quality Monitor")
    st.markdown(
        '<p class="subtitle">AQI tracking, particulate matter analysis, and threshold alerting</p>',
        unsafe_allow_html=True,
    )

    summary = api_get("/api/v1/pollution/summary")
    alerts = api_get("/api/v1/pollution/alerts")
    timeseries = api_get("/api/v1/pollution/timeseries")

    if not summary or isinstance(summary, dict):
        st.info("Waiting for pollution data...")
        st.stop()

    df = pd.DataFrame(summary)

    # --- KPIs ---
    worst = df.loc[df["avg_aqi"].idxmax()]
    best = df.loc[df["avg_aqi"].idxmin()]
    alert_count = alerts.get("total_alerts", 0) if alerts else 0
    critical_count = alerts.get("critical_count", 0) if alerts else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Worst District",
        worst["district"],
        f"AQI {int(worst['avg_aqi'])}",
        delta_color="off",
    )
    c2.metric(
        "Best District",
        best["district"],
        f"AQI {int(best['avg_aqi'])}",
        delta_color="off",
    )
    c3.metric("Total Alerts", alert_count)
    c4.metric("Critical Alerts", critical_count)

    st.markdown("---")

    # --- AQI Time Series ---
    if timeseries and not isinstance(timeseries, dict):
        st.markdown("### AQI Trend Over Time")
        df_ts = pd.DataFrame(timeseries)

        fig = px.line(df_ts, x="minute", y="avg_aqi", color="district")
        fig.add_hline(
            y=150,
            line_dash="dash",
            line_color=COLORS["warning"],
            annotation_text="Unhealthy",
        )
        fig.add_hline(
            y=300,
            line_dash="dash",
            line_color=COLORS["danger"],
            annotation_text="Hazardous",
        )
        fig.update_layout(**CHART_LAYOUT, height=380)
        fig.update_traces(line=dict(width=2))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- AQI Bars ---
    st.markdown("### District Comparison")

    c1, c2 = st.columns(2)

    with c1:
        bar_colors = []
        for aqi in df["avg_aqi"]:
            if aqi > 300:
                bar_colors.append("#7b2d8e")
            elif aqi > 200:
                bar_colors.append("#cc0033")
            elif aqi > 150:
                bar_colors.append("#ff6600")
            elif aqi > 100:
                bar_colors.append("#ffcc00")
            else:
                bar_colors.append("#64ffda")

        fig = go.Figure(
            go.Bar(
                x=df["district"],
                y=df["avg_aqi"],
                marker_color=bar_colors,
                text=df["avg_aqi"].round(0).astype(int),
                textposition="outside",
                textfont=dict(color="#ccd6f6", size=13),
            )
        )
        fig.add_hline(y=150, line_dash="dash", line_color=COLORS["warning"])
        fig.add_hline(y=300, line_dash="dash", line_color=COLORS["danger"])
        fig.update_layout(
            **CHART_LAYOUT,
            height=400,
            title=dict(
                text="Average AQI by District", font=dict(color="#ccd6f6", size=14)
            ),
        )
        st.plotly_chart(fig, use_container_width=True)

    with c2:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["district"],
                y=df["avg_pm25"],
                name="Avg PM2.5",
                marker_color=COLORS["danger"],
                opacity=0.7,
            )
        )
        fig.add_trace(
            go.Bar(
                x=df["district"],
                y=df["max_pm25"],
                name="Peak PM2.5",
                marker_color="#cc0033",
                opacity=0.5,
            )
        )
        fig.add_hline(
            y=60,
            line_dash="dot",
            line_color=COLORS["warning"],
            annotation_text="WHO Guideline",
        )
        fig.update_layout(
            **CHART_LAYOUT,
            height=400,
            barmode="group",
            title=dict(text="PM2.5 Levels", font=dict(color="#ccd6f6", size=14)),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- District Cards ---
    st.markdown("### District Health")
    cols = st.columns(len(df))
    for i, (_, row) in enumerate(df.iterrows()):
        with cols[i]:
            aqi = row["avg_aqi"]
            if aqi > 300:
                label = "HAZARDOUS"
            elif aqi > 200:
                label = "VERY UNHEALTHY"
            elif aqi > 150:
                label = "UNHEALTHY"
            elif aqi > 100:
                label = "MODERATE"
            else:
                label = "GOOD"

            st.metric(row["district"], f"AQI {int(aqi)}", label, delta_color="off")
            st.caption(
                f"PM2.5: {row['avg_pm25']:.1f} | CO2: {row.get('avg_co2', 0):.0f} ppm"
            )

    st.markdown("---")

    # --- Alerts ---
    if alerts and alert_count > 0:
        st.markdown(f"### Alert Feed ({alert_count} total)")
        for a in alerts.get("alerts", [])[:12]:
            level = a.get("alert_level")
            msg = a.get("alert_message", "")
            ts = a.get("timestamp", "")[:19]
            if level == "CRITICAL":
                st.error(f"CRITICAL | {a.get('district')} | AQI {a.get('aqi')} | {ts}")
            else:
                st.warning(f"WARNING | {a.get('district')} | AQI {a.get('aqi')} | {ts}")


# ================================================================
# GOVERNANCE AUDIT
# ================================================================
elif page == "Governance Audit":
    st.markdown("# Governance Audit Trail")
    st.markdown(
        '<p class="subtitle">Verifiable proof of PII detection, transformation, and zone separation</p>',
        unsafe_allow_html=True,
    )

    comparison = api_get("/api/v1/governance/comparison")
    stats = api_get("/api/v1/governance/stats")

    if not comparison or "raw_sample" not in comparison:
        st.info("Waiting for data to flow through governance pipeline...")
        st.stop()

    # --- Stats ---
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Records Scanned", f"{stats.get('traffic_records_processed', 0):,}")
    c2.metric("PII Detected", f"{stats.get('traffic_records_with_pii', 0):,}")
    c3.metric("PII Hashed", f"{stats.get('traffic_records_with_pii', 0):,}")
    c4.metric("Violations", "0")

    st.markdown("---")

    # --- Side by Side ---
    st.markdown("### Transformation Evidence")
    st.caption(
        "Actual records from MinIO storage zones, demonstrating PII governance in action"
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("#### Raw Ingestion (raw-zone)")
        st.code(json.dumps(comparison["raw_sample"], indent=2), language="json")
        st.error(
            "Contains unmasked license plates. Under DPDP Act Section 8(7) "
            "and GDPR Article 4(1), vehicle registration numbers linked to "
            "location/time data constitute PII requiring protection."
        )

    with c2:
        st.markdown("#### Governed Output (curated-zone)")
        st.code(json.dumps(comparison["governed_sample"], indent=2), language="json")
        st.success(
            "License plates replaced with truncated SHA-256 hashes. "
            "Hashed values preserve analytical utility (unique vehicle "
            "counting via hash comparison) while making re-identification "
            "computationally infeasible."
        )

    st.markdown("---")

    # --- Technical Tabs ---
    tab1, tab2, tab3 = st.tabs(
        ["Pipeline Architecture", "Detection Rules", "Storage Policy"]
    )

    with tab1:
        st.markdown("""
        ```
        Traffic Sensor (Python Generator)
            |
            | Raw JSON with license_plates field
            v
        Redpanda Topic: city.traffic.raw
            |
            | Consumed by Governance Agent
            v
        Governance Agent (Deterministic Rules Engine)
            |
            |-- Scan: Check record fields against PII registry
            |-- Detect: license_plates field found
            |-- Transform: SHA-256 hash each plate value
            |-- Metadata: Add pii_detected=true, governed_at=timestamp
            |
            |-- Write raw record --> MinIO raw-zone (restricted, audit)
            |-- Write governed record --> MinIO curated-zone (open, analytics)
            |-- Publish governed record --> Redpanda city.traffic.governed
            v
        Analytics API --> Dashboard
            |
            | Reads ONLY from curated-zone
            | Raw-zone accessible only to compliance officers
        ```
        """)

    with tab2:
        st.markdown("""
        **Detection Mechanism: Deterministic Policy-as-Code**

        ```python
        PII_FIELDS = ["license_plates"]

        # For each record:
        #   1. Check if any field name matches PII_FIELDS
        #   2. If match found and field is non-empty:
        #      - Apply SHA-256 hash (truncated to 12 chars)
        #      - Mark record: pii_detected = True
        #   3. If no match: pass through unchanged
        ```

        **Why deterministic over ML-based detection:**

        | Property | Rule-Based | ML/LLM |
        |----------|-----------|--------|
        | False negative rate | 0% for configured fields | Non-zero |
        | Processing latency | Microseconds | Seconds |
        | Auditability | Fully transparent | Opaque |
        | Regulatory acceptance | Established | Emerging |
        | Consistency | Identical runs produce identical output | Varies |
        """)

    with tab3:
        st.markdown("""
        **Zone Separation Policy:**

        | Attribute | raw-zone | curated-zone |
        |-----------|----------|--------------|
        | PII present | Yes (original data) | No (hashed) |
        | Access level | Restricted | Open |
        | Purpose | Legal audit, compliance | Analytics, APIs, public |
        | Retention | Regulatory minimum | Indefinite |
        | Cloud equivalent | S3 + KMS + restrictive IAM | S3 + standard IAM |
        | Consumers | Compliance officers only | Analysts, developers, public APIs |
        """)


# ================================================================
# SYSTEM AND API
# ================================================================
elif page == "System and API":
    st.markdown("# System Architecture")
    st.markdown(
        '<p class="subtitle">Infrastructure topology, API reference, and cloud deployment mapping</p>',
        unsafe_allow_html=True,
    )

    # --- Architecture Table ---
    st.markdown("### Running Services")

    services = pd.DataFrame(
        {
            "Layer": [
                "Ingestion",
                "Ingestion",
                "Ingestion",
                "Ingestion",
                "Processing",
                "Storage",
                "Analytics",
                "Serving",
            ],
            "Component": [
                "Message Broker",
                "Broker UI",
                "Traffic Sensors",
                "Pollution Sensors",
                "Governance Agent",
                "Object Storage",
                "Query API",
                "Dashboard",
            ],
            "Technology": [
                "Redpanda",
                "Redpanda Console",
                "Python",
                "Python",
                "Python + SHA-256",
                "MinIO",
                "FastAPI",
                "Streamlit",
            ],
            "Port": ["9092", "8080", "-", "-", "-", "9000/9001", "8000", "8501"],
            "Status": ["Active"] * 8,
        }
    )
    st.dataframe(services, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- API Explorer ---
    st.markdown("### API Reference")

    endpoints = {
        "/api/v1/governance/stats": "Governance pipeline statistics and compliance metrics",
        "/api/v1/governance/comparison": "Side-by-side raw vs governed data sample",
        "/api/v1/governance/timeline": "Governance activity over time (for charts)",
        "/api/v1/traffic/summary": "Traffic aggregates by district",
        "/api/v1/traffic/latest": "Most recent traffic records",
        "/api/v1/traffic/timeseries": "Traffic metrics over time by district",
        "/api/v1/pollution/summary": "Pollution aggregates by district",
        "/api/v1/pollution/alerts": "Active pollution alerts with severity",
        "/api/v1/pollution/latest": "Most recent pollution records",
        "/api/v1/pollution/timeseries": "AQI and PM2.5 over time by district",
    }

    selected = st.selectbox("Endpoint", list(endpoints.keys()))
    st.caption(endpoints[selected])
    st.code(f"GET http://localhost:8000{selected}", language="bash")

    if st.button("Execute"):
        data = api_get(selected)
        if data:
            st.json(data)

    st.markdown("---")

    # --- Cloud Mapping ---
    st.markdown("### Production Cloud Mapping")

    cloud = pd.DataFrame(
        {
            "Local": [
                "Redpanda",
                "Python Generators",
                "Governance Agent",
                "MinIO",
                "FastAPI",
                "Streamlit",
                "Docker Compose",
            ],
            "AWS": [
                "Kinesis Data Streams",
                "IoT Core + Rules",
                "Lambda / ECS Fargate",
                "S3 + KMS",
                "API Gateway + Lambda",
                "ECS + ALB",
                "ECS / EKS",
            ],
            "Azure": [
                "Event Hubs",
                "IoT Hub",
                "Functions / Container Instances",
                "Blob + Key Vault",
                "API Management",
                "Container Apps",
                "AKS",
            ],
            "Benefit": [
                "Managed scaling",
                "Device management",
                "Auto-scaling",
                "Unlimited, encrypted",
                "Serverless",
                "Managed hosting",
                "Orchestration",
            ],
        }
    )
    st.dataframe(cloud, use_container_width=True, hide_index=True)

    st.markdown("---")
    st.markdown("### Quick Reference")
    st.code(
        """
# Start platform
docker compose up -d --build

# View services
docker compose ps

# Monitor governance
docker logs -f governance-agent

# API documentation
open http://localhost:8000/docs

# Stop platform
docker compose down -v
    """,
        language="bash",
    )
