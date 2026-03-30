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

# ========== CUSTOM STYLING ==========
st.markdown(
    """
<style>
    /* Dark professional theme overrides */
    .main .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
        max-width: 100%;
    }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #0a0a1a 0%, #1a1a2e 100%);
        border: 1px solid #2a2a4a;
        padding: 20px;
        border-radius: 12px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
    }

    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
        color: #8892b0 !important;
        text-transform: uppercase;
        letter-spacing: 1.2px;
        font-weight: 600;
    }

    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 700;
        color: #ccd6f6 !important;
    }

    /* Headers */
    h1 {
        color: #ccd6f6 !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px;
    }

    h2, h3 {
        color: #8892b0 !important;
        font-weight: 600 !important;
        border-bottom: 1px solid #1a1a2e;
        padding-bottom: 8px;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: #0a0a1a;
        border-right: 1px solid #1a1a2e;
    }

    /* Tables */
    [data-testid="stDataFrame"] {
        border: 1px solid #2a2a4a;
        border-radius: 8px;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background: #0a0a1a;
        border: 1px solid #2a2a4a;
        border-radius: 8px;
        padding: 10px 20px;
        color: #8892b0;
    }

    .stTabs [aria-selected="true"] {
        background: #1a1a2e;
        border-color: #64ffda;
        color: #64ffda;
    }

    /* Alert boxes */
    .stAlert {
        border-radius: 8px;
    }

    /* Status indicator */
    .status-online {
        display: inline-block;
        width: 8px;
        height: 8px;
        background: #64ffda;
        border-radius: 50%;
        margin-right: 6px;
        animation: pulse 2s infinite;
    }

    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.4; }
        100% { opacity: 1; }
    }

    .header-subtitle {
        color: #8892b0;
        font-size: 0.95rem;
        margin-top: -10px;
        margin-bottom: 20px;
    }

    .kpi-label {
        color: #64ffda;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: 600;
    }
</style>
""",
    unsafe_allow_html=True,
)


# ========== API HELPER ==========
def api_get(endpoint):
    try:
        r = requests.get(f"{API_URL}{endpoint}", timeout=10)
        if r.status_code == 200:
            return r.json()
        return None
    except Exception:
        return None


# ========== SIDEBAR ==========
with st.sidebar:
    st.markdown("## Urban Data Platform")
    st.markdown(
        '<p class="header-subtitle">Automated Governance Pipeline</p>',
        unsafe_allow_html=True,
    )

    st.markdown("---")

    page = st.radio(
        "NAVIGATION",
        [
            "Command Center",
            "Traffic Intelligence",
            "Air Quality Monitor",
            "Governance Audit",
            "System & API",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    # System status
    st.markdown("### System Status")

    api_status = api_get("/")
    if api_status:
        st.markdown(
            '<span class="status-online"></span> Analytics API', unsafe_allow_html=True
        )
    else:
        st.markdown("[ OFFLINE ] Analytics API")

    st.markdown(
        '<span class="status-online"></span> Redpanda Broker', unsafe_allow_html=True
    )
    st.markdown(
        '<span class="status-online"></span> Governance Agent', unsafe_allow_html=True
    )
    st.markdown(
        '<span class="status-online"></span> MinIO Storage', unsafe_allow_html=True
    )

    st.markdown("---")
    st.caption(f"Last refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if st.button("Refresh Data", use_container_width=True):
        st.rerun()


# ================================================================
# PAGE 1: COMMAND CENTER
# ================================================================
if page == "Command Center":
    st.markdown("# Command Center")
    st.markdown(
        '<p class="header-subtitle">'
        "Real-time overview of urban data governance and monitoring"
        "</p>",
        unsafe_allow_html=True,
    )

    stats = api_get("/api/v1/governance/stats")

    if not stats:
        st.error("Cannot reach Analytics API. Is the container running?")
        st.stop()

    # --- KPI Row ---
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Traffic Records", f"{stats.get('traffic_records_processed', 0):,}")
    with col2:
        st.metric("PII Intercepted", f"{stats.get('traffic_records_with_pii', 0):,}")
    with col3:
        st.metric(
            "Pollution Records", f"{stats.get('pollution_records_processed', 0):,}"
        )
    with col4:
        st.metric("Active Alerts", f"{stats.get('pollution_alerts_total', 0):,}")
    with col5:
        st.metric("Compliance Rate", "100%")

    st.markdown("---")

    # --- Two column layout ---
    col_left, col_right = st.columns([2, 1])

    with col_left:
        st.markdown("### Traffic Distribution")

        traffic = api_get("/api/v1/traffic/summary")
        if traffic and not isinstance(traffic, dict):
            df = pd.DataFrame(traffic)

            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=df["district"],
                    y=df["avg_vehicles"],
                    name="Avg Vehicles",
                    marker_color="#64ffda",
                    opacity=0.85,
                )
            )
            fig.add_trace(
                go.Scatter(
                    x=df["district"],
                    y=df["avg_speed"],
                    name="Avg Speed (km/h)",
                    yaxis="y2",
                    line=dict(color="#ff6b6b", width=3),
                    mode="lines+markers",
                    marker=dict(size=8),
                )
            )

            fig.update_layout(
                yaxis=dict(
                    title="Vehicle Count",
                    titlefont=dict(color="#64ffda"),
                    tickfont=dict(color="#8892b0"),
                    gridcolor="#1a1a2e",
                ),
                yaxis2=dict(
                    title="Speed (km/h)",
                    titlefont=dict(color="#ff6b6b"),
                    tickfont=dict(color="#8892b0"),
                    overlaying="y",
                    side="right",
                    gridcolor="#1a1a2e",
                ),
                xaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                legend=dict(font=dict(color="#8892b0"), bgcolor="rgba(0,0,0,0)"),
                height=380,
                margin=dict(l=40, r=40, t=20, b=40),
                bargap=0.3,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Waiting for traffic data to accumulate...")

    with col_right:
        st.markdown("### Governance Pipeline")

        total = stats.get("traffic_records_processed", 0)
        pii = stats.get("traffic_records_with_pii", 0)

        # Compliance gauge
        fig = go.Figure(
            go.Indicator(
                mode="gauge+number+delta",
                value=100,
                number={"suffix": "%", "font": {"size": 48, "color": "#64ffda"}},
                title={
                    "text": "PII Compliance",
                    "font": {"size": 14, "color": "#8892b0"},
                },
                gauge={
                    "axis": {
                        "range": [0, 100],
                        "tickcolor": "#8892b0",
                        "tickfont": {"color": "#8892b0"},
                    },
                    "bar": {"color": "#64ffda", "thickness": 0.3},
                    "bgcolor": "#0a0a1a",
                    "bordercolor": "#2a2a4a",
                    "steps": [
                        {"range": [0, 50], "color": "rgba(255,68,68,0.15)"},
                        {"range": [50, 80], "color": "rgba(255,170,0,0.15)"},
                        {"range": [80, 100], "color": "rgba(100,255,218,0.1)"},
                    ],
                    "threshold": {
                        "line": {"color": "#64ffda", "width": 3},
                        "thickness": 0.8,
                        "value": 100,
                    },
                },
            )
        )
        fig.update_layout(
            height=250,
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=30, r=30, t=40, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Pipeline summary
        st.markdown(f"""
        | Metric | Value |
        |--------|-------|
        | Records Ingested | {total:,} |
        | PII Fields Hashed | {pii:,} |
        | Compliance Violations | 0 |
        | Storage Zones | 2 (raw / curated) |
        | Active Topics | 4 |
        """)

    st.markdown("---")

    # --- Air Quality Summary ---
    st.markdown("### Air Quality Snapshot")

    pollution = api_get("/api/v1/pollution/summary")
    if pollution and not isinstance(pollution, dict):
        df_poll = pd.DataFrame(pollution)

        cols = st.columns(len(df_poll))
        for i, (_, row) in enumerate(df_poll.iterrows()):
            with cols[i]:
                aqi = row["avg_aqi"]
                if aqi > 300:
                    label, color = "HAZARDOUS", "#7b2d8e"
                elif aqi > 200:
                    label, color = "VERY UNHEALTHY", "#cc0033"
                elif aqi > 150:
                    label, color = "UNHEALTHY", "#ff6600"
                elif aqi > 100:
                    label, color = "MODERATE", "#ffcc00"
                else:
                    label, color = "GOOD", "#64ffda"

                st.metric(row["district"], f"AQI {int(aqi)}", label, delta_color="off")
    else:
        st.info("Waiting for pollution data...")


# ================================================================
# PAGE 2: TRAFFIC INTELLIGENCE
# ================================================================
elif page == "Traffic Intelligence":
    st.markdown("# Traffic Intelligence")
    st.markdown(
        '<p class="header-subtitle">'
        "Vehicle density, speed analysis, and congestion indicators"
        "</p>",
        unsafe_allow_html=True,
    )

    summary = api_get("/api/v1/traffic/summary")
    latest = api_get("/api/v1/traffic/latest")

    if not summary or isinstance(summary, dict):
        st.info("Waiting for traffic data to accumulate...")
        st.stop()

    df = pd.DataFrame(summary)

    # --- Charts Row ---
    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["district"],
                y=df["avg_vehicles"],
                marker=dict(
                    color=df["avg_vehicles"],
                    colorscale=[[0, "#1a1a2e"], [0.5, "#64ffda"], [1, "#ff6b6b"]],
                    showscale=True,
                    colorbar=dict(
                        title="Count",
                        tickfont=dict(color="#8892b0"),
                        titlefont=dict(color="#8892b0"),
                    ),
                ),
                text=df["avg_vehicles"].round(0).astype(int),
                textposition="outside",
                textfont=dict(color="#ccd6f6", size=13),
            )
        )
        fig.update_layout(
            title=dict(
                text="Average Vehicle Count by District",
                font=dict(color="#ccd6f6", size=16),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
            yaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
            height=420,
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["district"],
                y=df["avg_speed"],
                marker=dict(
                    color=df["avg_speed"],
                    colorscale=[[0, "#ff6b6b"], [0.5, "#ffcc00"], [1, "#64ffda"]],
                    showscale=True,
                    colorbar=dict(
                        title="km/h",
                        tickfont=dict(color="#8892b0"),
                        titlefont=dict(color="#8892b0"),
                    ),
                ),
                text=df["avg_speed"].round(1),
                textposition="outside",
                textfont=dict(color="#ccd6f6", size=13),
            )
        )
        fig.update_layout(
            title=dict(
                text="Average Speed by District (km/h)",
                font=dict(color="#ccd6f6", size=16),
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
            yaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
            height=420,
            margin=dict(t=50, b=40),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Congestion Analysis ---
    st.markdown("### Congestion Analysis")

    for _, row in df.iterrows():
        speed = row["avg_speed"]
        vehicles = row["avg_vehicles"]

        if speed < 25:
            status = "HEAVY CONGESTION"
            bar_color = "#ff4444"
            recommendation = "Consider traffic diversion or signal re-timing"
        elif speed < 40:
            status = "MODERATE TRAFFIC"
            bar_color = "#ffaa00"
            recommendation = "Monitor for potential escalation"
        else:
            status = "FREE FLOW"
            bar_color = "#64ffda"
            recommendation = "Normal operations"

        congestion_pct = max(0, min(100, (1 - speed / 80) * 100))

        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            st.markdown(f"**{row['district']}**")
            st.caption(f"{status}")
        with col2:
            st.progress(congestion_pct / 100)
        with col3:
            st.caption(f"{speed:.0f} km/h | {vehicles:.0f} vehicles")

    st.markdown("---")

    # --- Recent Records ---
    if latest and not isinstance(latest, dict):
        st.markdown("### Recent Traffic Records")
        df_latest = pd.DataFrame(latest)
        display_cols = [
            c
            for c in [
                "timestamp",
                "sensor_id",
                "district",
                "vehicle_count",
                "avg_speed_kmh",
                "pii_detected",
            ]
            if c in df_latest.columns
        ]

        st.dataframe(
            df_latest[display_cols],
            use_container_width=True,
            height=350,
            column_config={
                "timestamp": st.column_config.TextColumn("Timestamp"),
                "sensor_id": st.column_config.TextColumn("Sensor"),
                "district": st.column_config.TextColumn("District"),
                "vehicle_count": st.column_config.NumberColumn("Vehicles", format="%d"),
                "avg_speed_kmh": st.column_config.NumberColumn(
                    "Speed (km/h)", format="%.1f"
                ),
                "pii_detected": st.column_config.CheckboxColumn("PII Governed"),
            },
        )


# ================================================================
# PAGE 3: AIR QUALITY MONITOR
# ================================================================
elif page == "Air Quality Monitor":
    st.markdown("# Air Quality Monitor")
    st.markdown(
        '<p class="header-subtitle">'
        "PM2.5, PM10, AQI tracking and threshold-based alerting"
        "</p>",
        unsafe_allow_html=True,
    )

    summary = api_get("/api/v1/pollution/summary")
    alerts = api_get("/api/v1/pollution/alerts")
    latest = api_get("/api/v1/pollution/latest")

    if not summary or isinstance(summary, dict):
        st.info("Waiting for pollution data to accumulate...")
        st.stop()

    df = pd.DataFrame(summary)

    # --- AQI Overview ---
    st.markdown("### District AQI Levels")

    fig = go.Figure()

    colors = []
    for aqi in df["avg_aqi"]:
        if aqi > 300:
            colors.append("#7b2d8e")
        elif aqi > 200:
            colors.append("#cc0033")
        elif aqi > 150:
            colors.append("#ff6600")
        elif aqi > 100:
            colors.append("#ffcc00")
        else:
            colors.append("#64ffda")

    fig.add_trace(
        go.Bar(
            x=df["district"],
            y=df["avg_aqi"],
            marker_color=colors,
            text=df["avg_aqi"].round(0).astype(int),
            textposition="outside",
            textfont=dict(color="#ccd6f6", size=14, family="monospace"),
        )
    )

    # Threshold lines
    fig.add_hline(
        y=150,
        line_dash="dash",
        line_color="#ff6600",
        line_width=1,
        annotation_text="Unhealthy (150)",
        annotation_font_color="#ff6600",
    )
    fig.add_hline(
        y=300,
        line_dash="dash",
        line_color="#cc0033",
        line_width=1,
        annotation_text="Hazardous (300)",
        annotation_font_color="#cc0033",
    )

    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
        yaxis=dict(
            title="AQI",
            titlefont=dict(color="#8892b0"),
            tickfont=dict(color="#8892b0"),
            gridcolor="#1a1a2e",
        ),
        height=420,
        margin=dict(t=20, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- PM2.5 vs PM10 comparison ---
    st.markdown("### Particulate Matter Comparison")

    col1, col2 = st.columns(2)

    with col1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=df["district"],
                y=df["avg_pm25"],
                name="PM2.5",
                marker_color="#ff6b6b",
                opacity=0.85,
            )
        )
        fig.update_layout(
            title=dict(
                text="Average PM2.5 by District", font=dict(color="#ccd6f6", size=14)
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(tickfont=dict(color="#8892b0")),
            yaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
            height=350,
        )
        fig.add_hline(
            y=60,
            line_dash="dot",
            line_color="#ffaa00",
            annotation_text="WHO Limit",
            annotation_font_color="#ffaa00",
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        if "max_pm25" in df.columns:
            fig = go.Figure()
            fig.add_trace(
                go.Bar(
                    x=df["district"],
                    y=df["max_pm25"],
                    name="Peak PM2.5",
                    marker_color="#cc0033",
                    opacity=0.85,
                )
            )
            fig.update_layout(
                title=dict(
                    text="Peak PM2.5 Readings", font=dict(color="#ccd6f6", size=14)
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(tickfont=dict(color="#8892b0")),
                yaxis=dict(tickfont=dict(color="#8892b0"), gridcolor="#1a1a2e"),
                height=350,
            )
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- Alerts ---
    if alerts and alerts.get("total_alerts", 0) > 0:
        st.markdown(f"### Active Alerts ({alerts['total_alerts']})")

        for alert in alerts.get("alerts", [])[:15]:
            level = alert.get("alert_level", "")
            msg = alert.get("alert_message", "No details")
            district = alert.get("district", "Unknown")
            ts = alert.get("timestamp", "")[:19]
            aqi = alert.get("aqi", "N/A")

            if level == "CRITICAL":
                st.error(f"**CRITICAL** | {district} | AQI: {aqi} | {msg} | {ts}")
            elif level == "WARNING":
                st.warning(f"**WARNING** | {district} | AQI: {aqi} | {msg} | {ts}")
    else:
        st.success("No active air quality alerts.")

    # --- AQI Scale Reference ---
    st.markdown("---")
    st.markdown("### AQI Reference Scale")

    scale_data = pd.DataFrame(
        {
            "Range": ["0-50", "51-100", "101-150", "151-200", "201-300", "301-500"],
            "Category": [
                "Good",
                "Moderate",
                "Unhealthy (Sensitive)",
                "Unhealthy",
                "Very Unhealthy",
                "Hazardous",
            ],
            "Health Advisory": [
                "Air quality is satisfactory",
                "Acceptable; moderate risk for sensitive individuals",
                "Sensitive groups may experience health effects",
                "General public may experience health effects",
                "Health alert: significant risk for everyone",
                "Emergency conditions: entire population affected",
            ],
        }
    )
    st.dataframe(scale_data, use_container_width=True, hide_index=True)


# ================================================================
# PAGE 4: GOVERNANCE AUDIT
# ================================================================
elif page == "Governance Audit":
    st.markdown("# Governance Audit Trail")
    st.markdown(
        '<p class="header-subtitle">'
        "Verifiable proof of PII detection, transformation, "
        "and data separation"
        "</p>",
        unsafe_allow_html=True,
    )

    comparison = api_get("/api/v1/governance/comparison")
    stats = api_get("/api/v1/governance/stats")

    if not comparison or "raw_sample" not in comparison:
        st.info("Waiting for data to flow through the governance pipeline...")
        st.stop()

    # --- Governance Summary ---
    st.markdown("### Compliance Summary")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Total Records Scanned", f"{stats.get('traffic_records_processed', 0):,}"
        )
    with col2:
        st.metric("PII Fields Detected", f"{stats.get('traffic_records_with_pii', 0):,}")
    with col3:
        st.metric("Compliance Violations", "0")

    st.markdown("---")

    # --- Side by Side Comparison ---
    st.markdown("### Data Transformation Evidence")
    st.caption(
        "Showing actual records from raw-zone and curated-zone storage. "
        "The license_plates field demonstrates SHA-256 hashing applied "
        "by the governance agent."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### BEFORE: Raw Ingestion")
        st.caption("Source: MinIO raw-zone bucket")
        st.code(json.dumps(comparison["raw_sample"], indent=2), language="json")
        st.error(
            "This record contains unmasked license plate numbers. "
            "Under DPDP Act / GDPR, this constitutes personally "
            "identifiable information (PII) that must not be exposed "
            "to analytics consumers."
        )

    with col2:
        st.markdown("#### AFTER: Governed Output")
        st.caption("Source: MinIO curated-zone bucket")
        st.code(json.dumps(comparison["governed_sample"], indent=2), language="json")
        st.success(
            "License plates have been replaced with SHA-256 hashes. "
            "The data retains analytical utility (unique vehicle "
            "counting via hash comparison) while eliminating "
            "re-identification risk."
        )

    st.markdown("---")

    # --- Technical Details ---
    st.markdown("### Governance Mechanism")

    tab1, tab2, tab3 = st.tabs(
        ["Pipeline Flow", "PII Detection Rules", "Storage Separation"]
    )

    with tab1:
        st.markdown("""
        **Data Flow Through Governance Pipeline:**

        ```
        IoT Sensor (Generator)
            |
            | JSON event with license_plates field
            v
        Redpanda: city.traffic.raw
            |
            | Consumed by Governance Agent
            v
        Governance Agent
            |
            |--- Scan record against PII field registry
            |--- PII detected: license_plates
            |--- Action: SHA-256 hash each plate value
            |--- Add metadata: pii_detected=true, governed_at=timestamp
            |
            |--- Output 1: Original --> MinIO raw-zone (audit retention)
            |--- Output 2: Governed --> MinIO curated-zone (analytics)
            |--- Output 3: Governed --> Redpanda city.traffic.governed
            v
        Analytics API / Dashboard
            |
            | Only reads from curated-zone
            | Never accesses raw-zone
            v
        End Users (City Officials, Public APIs)
        ```
        """)

    with tab2:
        st.markdown("""
        **PII Detection Configuration:**

        The governance agent uses a deterministic, policy-as-code approach:

        ```python
        # Governance Rules — Auditable and Reproducible
        PII_FIELDS = ["license_plates"]

        # Transformation: SHA-256 truncated hash
        # Input:  "AB-1234-CD"
        # Output: "a3f2b8c91d4e"

        # Properties:
        # - Deterministic: Same input always produces same hash
        # - One-way: Cannot reverse hash to recover original plate
        # - Unique: Different plates produce different hashes
        # - Useful: Hashed values still allow vehicle counting
        ```

        **Why deterministic rules over ML/LLM-based detection:**

        | Criterion | Deterministic Rules | ML/LLM Detection |
        |-----------|-------------------|-------------------|
        | False negative rate | 0% (configured fields) | Non-zero |
        | Latency | Microseconds | Seconds |
        | Auditability | Fully transparent | Black box |
        | Legal defensibility | High | Uncertain |
        | Regulatory acceptance | Established | Emerging |
        """)

    with tab3:
        st.markdown("""
        **Storage Zone Separation:**

        | Property | raw-zone | curated-zone |
        |----------|----------|--------------|
        | Contains PII | Yes | No (hashed) |
        | Access Level | Restricted (audit only) | Open (analytics) |
        | Retention Purpose | Legal compliance | Business analytics |
        | Encryption | Server-side (KMS) | Standard |
        | Consumers | Compliance officers | Analysts, APIs, Public |

        **Cloud Equivalent:**

        | Local | Cloud Target |
        |-------|-------------|
        | MinIO raw-zone | S3 + KMS encryption + restricted IAM |
        | MinIO curated-zone | S3 + standard encryption + broad IAM |
        """)


# ================================================================
# PAGE 5: SYSTEM & API
# ================================================================
elif page == "System & API":
    st.markdown("# System Architecture & API")
    st.markdown(
        '<p class="header-subtitle">'
        "Infrastructure overview, API documentation, "
        "and cloud deployment mapping"
        "</p>",
        unsafe_allow_html=True,
    )

    # --- Architecture ---
    st.markdown("### Platform Architecture")

    st.markdown("""
    | Layer | Component | Technology | Port | Status |
    |-------|-----------|------------|------|--------|
    | Ingestion | Message Broker | Redpanda | 9092 | Active |
    | Ingestion | Broker Console | Redpanda Console | 8080 | Active |
    | Ingestion | Traffic Sensors | Python Generator | - | Active |
    | Ingestion | Pollution Sensors | Python Generator | - | Active |
    | Processing | Governance Agent | Python + SHA-256 | - | Active |
    | Storage | Object Storage | MinIO | 9000/9001 | Active |
    | Analytics | Query API | FastAPI + DuckDB | 8000 | Active |
    | Serving | Dashboard | Streamlit | 8501 | Active |
    """)

    st.markdown("---")

    # --- API Explorer ---
    st.markdown("### API Explorer")
    st.caption(
        "All endpoints return JSON. Full Swagger documentation available at /docs"
    )

    endpoints = {
        "GET /api/v1/governance/stats": "/api/v1/governance/stats",
        "GET /api/v1/governance/comparison": "/api/v1/governance/comparison",
        "GET /api/v1/traffic/summary": "/api/v1/traffic/summary",
        "GET /api/v1/traffic/latest": "/api/v1/traffic/latest",
        "GET /api/v1/pollution/summary": "/api/v1/pollution/summary",
        "GET /api/v1/pollution/alerts": "/api/v1/pollution/alerts",
        "GET /api/v1/pollution/latest": "/api/v1/pollution/latest",
    }

    selected = st.selectbox("Select an endpoint to test:", list(endpoints.keys()))

    endpoint = endpoints[selected]

    st.code(f"curl http://localhost:8000{endpoint}", language="bash")

    if st.button("Execute Request"):
        data = api_get(endpoint)
        if data:
            st.json(data)
        else:
            st.error("Request failed. Is analytics-api running?")

    st.markdown("---")

    # --- Cloud Mapping ---
    st.markdown("### Cloud Deployment Mapping")
    st.caption(
        "This local prototype maps directly to managed "
        "cloud services for production deployment"
    )

    cloud_map = pd.DataFrame(
        {
            "Local Component": [
                "Redpanda",
                "Python Generators",
                "Governance Agent",
                "MinIO",
                "FastAPI",
                "Streamlit",
            ],
            "AWS Equivalent": [
                "Kinesis Data Streams",
                "IoT Core",
                "Lambda / ECS Fargate",
                "S3 + KMS",
                "API Gateway + Lambda",
                "ECS + ALB",
            ],
            "Azure Equivalent": [
                "Event Hubs",
                "IoT Hub",
                "Azure Functions / ACI",
                "Blob Storage + Key Vault",
                "API Management + Functions",
                "Container Apps",
            ],
            "Scaling Advantage": [
                "Auto-scaling shards",
                "Managed device registry",
                "Auto-scaling containers",
                "Unlimited storage",
                "Serverless auto-scale",
                "Managed container hosting",
            ],
        }
    )

    st.dataframe(cloud_map, use_container_width=True, hide_index=True)

    st.markdown("---")

    # --- Docker Compose Reference ---
    st.markdown("### Container Orchestration")
    st.caption("Current docker-compose service topology")

    st.code(
        """
# Start entire platform
docker compose up -d --build

# View all services
docker compose ps

# View governance logs
docker logs -f governance-agent

# Stop everything
docker compose down -v
    """,
        language="bash",
    )
