<div align="center">

# Smart City Data Platform

**Automated Data Governance for Urban Traffic & Pollution Monitoring**

[![CI/CD](https://github.com/YOUR_USERNAME/smart-city-platform/actions/workflows/pipeline-ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/smart-city-platform/actions)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docker.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Redpanda](https://img.shields.io/badge/Redpanda-Kafka_Compatible-E03C31?logo=apache-kafka&logoColor=white)](https://redpanda.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-10_Endpoints-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

A cloud-native streaming data platform that ingests simulated urban IoT sensor data, applies **automated PII governance** (SHA-256 hashing of license plates), separates raw audit data from governed analytics data, and serves everything through **REST APIs** and a **5-page interactive dashboard**.

**10 containers** · **100% PII compliance** · **20 unit tests** · **single-command deployment**

---

[Quick Start](#-quick-start) ·
[Architecture](#-architecture) ·
[Features](#-features) ·
[API Reference](#-api-reference) ·
[Dashboard](#-dashboard) ·
[Testing](#-testing) ·
[Cloud Mapping](#-cloud-deployment-mapping)

</div>

---

## Table of Contents

- [Overview](#-overview)
- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Features](#-features)
- [Services](#-services)
- [Data Governance](#-data-governance)
- [API Reference](#-api-reference)
- [Dashboard](#-dashboard)
- [Monitoring](#-monitoring)
- [Testing](#-testing)
- [CI/CD Pipeline](#-cicd-pipeline)
- [Security](#-security)
- [Cloud Deployment Mapping](#-cloud-deployment-mapping)
- [Project Structure](#-project-structure)
- [Troubleshooting](#-troubleshooting)
- [Contributing](#-contributing)

---

## Overview

Urban sensor networks generate massive streams of traffic and pollution data. This data frequently contains **Personally Identifiable Information** (PII) — specifically vehicle license plate numbers — that must be protected under regulations like **India's DPDP Act 2023** and **EU's GDPR**.

This platform solves the fundamental tension between **analytical utility** and **privacy compliance** by applying governance at the stream processing layer:

```
Raw Sensor Data → Stream Broker → Governance Agent → Governed Data → APIs + Dashboard
                                       |
                                       ├── PII detected? → SHA-256 hash
                                       ├── Save original → raw-zone (audit)
                                       └── Save governed → curated-zone (analytics)
```

**No PII ever reaches the analytics layer.** Period.

### Why This Matters

| Problem                    | Traditional Approach                    | This Platform                                    |
| -------------------------- | --------------------------------------- | ------------------------------------------------ |
| PII in analytics databases | Manual audit (days/weeks)               | Automated stream-level governance (microseconds) |
| Compliance evidence        | Retrospective reports                   | Real-time dashboard with live proof              |
| Detection accuracy         | Human error-prone                       | Deterministic: 100% for configured fields        |
| Open data readiness        | Requires separate sanitization pipeline | curated-zone is always safe to publish           |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2+)
- 4GB+ available RAM

### One Command Deploy

```bash
git clone https://github.com/YOUR_USERNAME/smart-city-platform.git
cd smart-city-platform
docker compose up -d --build
```

Wait ~30 seconds for all services to initialize, then:

| Service              | URL                                               | Credentials            |
| -------------------- | ------------------------------------------------- | ---------------------- |
| **Dashboard**        | [localhost:8501](http://localhost:8501)           | —                      |
| **API Docs**         | [localhost:8000/docs](http://localhost:8000/docs) | —                      |
| **Redpanda Console** | [localhost:8080](http://localhost:8080)           | —                      |
| **MinIO Console**    | [localhost:9001](http://localhost:9001)           | `admin` / `admin12345` |
| **Grafana**          | [localhost:3000](http://localhost:3000)           | `admin` / `admin`      |
| **Prometheus**       | [localhost:9090](http://localhost:9090)           | —                      |

### Verify Everything Works

```bash
# Check all containers are running
docker compose ps

# Watch governance agent in action
docker logs -f governance-agent

# Hit the API
curl -s http://localhost:8000/api/v1/governance/stats | python3 -m json.tool

# Run unit tests
cd governance && python3 test_governance.py
```

### Stop

```bash
# Stop (preserves data)
docker compose down

# Stop and destroy all data
docker compose down -v
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SMART CITY PLATFORM                         │
│                                                                     │
│  INGESTION              PROCESSING              SERVING             │
│  ─────────              ──────────              ───────             │
│                                                                     │
│  ┌──────────┐     ┌──────────┐     ┌──────────────┐               │
│  │ Traffic   │────▶│ Redpanda │────▶│ Governance   │               │
│  │ Generator │     │ (Broker) │     │ Agent        │               │
│  └──────────┘     │          │     │              │               │
│                    │ Topics:  │     │ • PII Scan   │               │
│  ┌──────────┐     │ raw      │     │ • SHA-256    │               │
│  │ Pollution │────▶│ governed │     │ • Alerts     │               │
│  │ Generator │     └──────────┘     └──────┬───────┘               │
│  └──────────┘                              │                        │
│                                    ┌───────┴────────┐               │
│                                    ▼                ▼               │
│                             ┌──────────┐     ┌──────────┐          │
│                             │ MinIO    │     │ MinIO    │          │
│                             │ raw-zone │     │ curated  │          │
│                             │ (audit)  │     │ (safe)   │          │
│                             └──────────┘     └─────┬────┘          │
│                                                     │               │
│                                              ┌──────┴──────┐       │
│                                              ▼             ▼       │
│                                        ┌──────────┐ ┌──────────┐  │
│                                        │ FastAPI  │ │ Streamlit│  │
│                                        │ (10 API) │ │ (5 page) │  │
│                                        └──────────┘ └──────────┘  │
│                                                                     │
│  OBSERVABILITY: Prometheus ──▶ Grafana                             │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Traffic Generator** produces JSON events every 2s with `license_plates` (PII)
2. **Pollution Generator** produces JSON events every 3s with AQI/PM2.5 readings
3. **Redpanda** buffers messages in 4 topics (`city.traffic.raw`, `city.traffic.governed`, `city.pollution.raw`, `city.pollution.governed`)
4. **Governance Agent** consumes raw topics, hashes PII, classifies pollution alerts
5. **MinIO** stores raw data (audit) and governed data (analytics) in separate buckets
6. **FastAPI** serves 10 REST endpoints reading from curated-zone
7. **Streamlit** renders 5-page dashboard consuming the API
8. **Prometheus + Grafana** monitor pipeline health and throughput

---

## Features

### Data Governance

- **Deterministic PII detection** — field-level matching against configured PII registry
- **SHA-256 hashing** — irreversible, deterministic, analytically useful
- **100% detection rate** for configured fields (zero false negatives)
- **Dual-zone storage** — raw (audit) and curated (analytics) with isolated access
- **Governance metadata** — every record tagged with `pii_detected` and `governed_at`

### Stream Processing

- **Kafka-compatible streaming** via Redpanda (low memory, fast startup)
- **Concurrent processing** — traffic and pollution governed in parallel threads
- **Real-time throughput** — governance applied in microseconds per record

### Analytics & Visualization

- **10 REST endpoints** with auto-generated Swagger documentation
- **5-page dashboard** — Command Center, Traffic, Pollution, Governance Audit, System
- **Time-series analysis** — traffic volume and AQI trends over time
- **Alert classification** — NORMAL / WARNING / CRITICAL based on AQI thresholds

### Security & Compliance

- **Zone-separated storage** with distinct access policies
- **IAM role matrix** — least privilege access per role
- **Encryption at rest** — KMS for raw-zone, standard for curated-zone
- **Audit trail** — every original record preserved in raw-zone

### DevOps

- **Single-command deployment** — `docker compose up -d --build`
- **20 unit tests** across 4 test suites
- **CI/CD pipeline** via GitHub Actions (test → build → integration)
- **Pipeline observability** via Prometheus metrics and Grafana dashboards

---

## Services

| Container          | Technology              | Port      | Purpose                                 |
| ------------------ | ----------------------- | --------- | --------------------------------------- |
| `redpanda`         | Redpanda v23.3.5        | 9092      | Kafka-compatible message broker         |
| `redpanda-console` | Redpanda Console v2.3.8 | 8080      | Broker management UI                    |
| `minio`            | MinIO latest            | 9000/9001 | S3-compatible object storage            |
| `traffic-gen`      | Python 3.11             | —         | Simulated traffic camera data           |
| `pollution-gen`    | Python 3.11             | —         | Simulated air quality sensors           |
| `governance-agent` | Python 3.11             | —         | PII detection + SHA-256 hashing         |
| `analytics-api`    | FastAPI                 | 8000      | REST API + Swagger + Prometheus metrics |
| `dashboard`        | Streamlit               | 8501      | 5-page interactive dashboard            |
| `prometheus`       | Prometheus              | 9090      | Metrics collection                      |
| `grafana`          | Grafana                 | 3000      | Metrics visualization                   |

---

## Data Governance

### How It Works

```python
# Policy-as-Code: The single source of truth
PII_FIELDS = ["license_plates"]

# For each traffic record:
# 1. Check if any field matches PII_FIELDS
# 2. If match found → SHA-256 hash the values
# 3. Save original → raw-zone (restricted audit access)
# 4. Save governed → curated-zone (open analytics access)
# 5. Publish governed → city.traffic.governed topic
```

### Transformation Example

| Field               | Raw (raw-zone) | Governed (curated-zone) |
| ------------------- | -------------- | ----------------------- |
| `license_plates[0]` | `AB-1234-CD`   | `a3f2b8c91d4e`          |
| `license_plates[1]` | `EF-5678-GH`   | `7bc1e9f3a2d8`          |
| `pii_detected`      | _(absent)_     | `true`                  |
| `governed_at`       | _(absent)_     | `2025-03-29T21:04:15`   |

### Why Deterministic Rules (Not LLM)

| Criterion           | Deterministic Rules        | LLM Detection            |
| ------------------- | -------------------------- | ------------------------ |
| False negative rate | **0%** (configured fields) | Non-zero (hallucination) |
| Latency             | Microseconds               | 2–5 seconds              |
| Auditability        | Fully transparent          | Black box                |
| Legal defensibility | High                       | Uncertain                |
| Testability         | 20 unit tests              | Difficult                |
| Resources           | Minimal                    | 4–8 GB RAM               |

### Storage Zone Separation

| Property     | `raw-zone`                                         | `curated-zone`                  |
| ------------ | -------------------------------------------------- | ------------------------------- |
| Contains PII | Yes (original)                                     | No (hashed)                     |
| Access       | Restricted: governance agent + compliance officers | Open: analysts, APIs, dashboard |
| Purpose      | Legal audit trail                                  | Business analytics              |
| Cloud target | S3 + KMS + restrictive IAM                         | S3 + standard IAM               |

---

## API Reference

Base URL: `http://localhost:8000`

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs)

### Governance

| Method | Endpoint                        | Description                                |
| ------ | ------------------------------- | ------------------------------------------ |
| `GET`  | `/api/v1/governance/stats`      | Pipeline statistics and compliance metrics |
| `GET`  | `/api/v1/governance/comparison` | Side-by-side raw vs governed data sample   |
| `GET`  | `/api/v1/governance/timeline`   | Governance activity aggregated by minute   |

### Traffic

| Method | Endpoint                          | Description                           |
| ------ | --------------------------------- | ------------------------------------- |
| `GET`  | `/api/v1/traffic/summary`         | Traffic aggregates by district        |
| `GET`  | `/api/v1/traffic/latest?limit=25` | Most recent governed traffic records  |
| `GET`  | `/api/v1/traffic/timeseries`      | Traffic metrics over time by district |

### Pollution

| Method | Endpoint                            | Description                            |
| ------ | ----------------------------------- | -------------------------------------- |
| `GET`  | `/api/v1/pollution/summary`         | Pollution aggregates by district       |
| `GET`  | `/api/v1/pollution/alerts?limit=30` | Active alerts with severity            |
| `GET`  | `/api/v1/pollution/latest?limit=25` | Most recent governed pollution records |
| `GET`  | `/api/v1/pollution/timeseries`      | AQI and PM2.5 trends over time         |

### Observability

| Method | Endpoint   | Description                   |
| ------ | ---------- | ----------------------------- |
| `GET`  | `/metrics` | Prometheus-compatible metrics |

### Example

```bash
# Get governance statistics
curl -s http://localhost:8000/api/v1/governance/stats | python3 -m json.tool

# Response:
{
    "traffic_records_processed": 1000,
    "traffic_records_with_pii": 1000,
    "pii_detection_rate": 100.0,
    "pii_governance_rate": 100.0,
    "pollution_records_processed": 1000,
    "pollution_alerts_critical": 192,
    "pollution_alerts_warning": 214
}
```

---

## Dashboard

5-page Streamlit dashboard at [localhost:8501](http://localhost:8501):

### Pages

| Page                     | Target User           | Key Features                                              |
| ------------------------ | --------------------- | --------------------------------------------------------- |
| **Command Center**       | City Administrator    | KPIs, compliance gauge, pipeline timeline, district cards |
| **Traffic Intelligence** | Traffic Engineer      | Vehicle density, speed charts, congestion progress bars   |
| **Air Quality Monitor**  | Environmental Officer | AQI bars, PM2.5 comparison, alert feed, health cards      |
| **Governance Audit**     | Compliance Officer    | Raw vs governed evidence, pipeline flow, detection rules  |
| **System & API**         | Developer             | Architecture table, API explorer, cloud mapping           |

<!--
### Screenshots

Add screenshots here:
![Command Center](screenshots/dash_command_center.png)
![Traffic Intelligence](screenshots/dash_traffic.png)
![Air Quality](screenshots/dash_pollution.png)
![Governance Audit](screenshots/dash_governance.png)
-->

---

## Monitoring

### Prometheus Metrics

The analytics API exports metrics at `/metrics`:

| Metric                          | Type      | Description                   |
| ------------------------------- | --------- | ----------------------------- |
| `pipeline_records_total`        | Gauge     | Records by zone and data type |
| `governance_pii_detected_total` | Gauge     | Total PII records hashed      |
| `pollution_alerts_active`       | Gauge     | Current alerts by severity    |
| `api_requests_total`            | Counter   | Request count by endpoint     |
| `api_request_duration_seconds`  | Histogram | Request latency distribution  |

### Grafana Dashboard

Access Grafana at [localhost:3000](http://localhost:3000) (`admin`/`admin`).

Add Prometheus data source: `http://prometheus:9090`

Useful queries:

```promql
pipeline_records_total
governance_pii_detected_total
pollution_alerts_active
rate(api_requests_total[5m])
histogram_quantile(0.95, rate(api_request_duration_seconds_bucket[5m]))
```

---

## Testing

### Unit Tests

20 tests across 4 suites covering PII detection, hashing, data integrity, and edge cases:

```bash
cd governance
python3 test_governance.py
```

```
============================================================
  TestPIIDetection: Tests for PII detection logic
============================================================
  PASS  test_detects_license_plates_as_pii
  PASS  test_marks_pii_detected_true
  PASS  test_no_pii_in_pollution_data
  PASS  test_empty_plates_list_no_pii
  PASS  test_missing_plates_field_no_pii

============================================================
  TestHashing: Tests for SHA-256 hashing mechanism
============================================================
  PASS  test_plates_are_hashed_not_original
  PASS  test_hash_length_is_12
  PASS  test_hash_is_deterministic
  PASS  test_different_inputs_different_hashes
  PASS  test_list_hashing
  PASS  test_hash_matches_manual_sha256

============================================================
  TestDataIntegrity: Tests ensuring governance doesn't corrupt data
============================================================
  PASS  test_original_record_unchanged
  PASS  test_non_pii_fields_preserved
  PASS  test_governed_record_has_pii_detected_field
  PASS  test_multiple_plates_all_hashed
  PASS  test_governed_is_separate_object

============================================================
  TestEdgeCases: Edge case handling
============================================================
  PASS  test_single_plate
  PASS  test_many_plates
  PASS  test_empty_record
  PASS  test_record_with_extra_fields

============================================================
  RESULTS: 20/20 passed, 0 failed
============================================================
```

### Load Test

```bash
cd security
python3 load_test.py
```

Measures sustained pipeline throughput by observing record accumulation over time windows.

---

## CI/CD Pipeline

GitHub Actions pipeline with 3 stages:

```
Push to master
    │
    ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Unit Tests  │────▶│  Build All   │────▶│ Integration  │
│  (20 tests)  │     │  Containers  │     │    Test      │
│  Python 3.11 │     │  (4 images)  │     │ Health checks│
└──────────────┘     └──────────────┘     └──────────────┘
```

Pipeline definition: [`.github/workflows/pipeline-ci.yml`](.github/workflows/pipeline-ci.yml)

---

## Security

### IAM Role Access Matrix

| Role               | raw-zone   | curated-zone | API             | Dashboard |
| ------------------ | ---------- | ------------ | --------------- | --------- |
| Governance Agent   | Read/Write | Write        | —               | —         |
| Compliance Officer | Read       | Read         | Read            | Read      |
| Data Analyst       | **Denied** | Read         | Read            | Read      |
| API Consumer       | **Denied** | Read         | Read            | —         |
| Public             | **Denied** | **Denied**   | Read (governed) | View      |

### Encryption

| Layer                       | Mechanism     | Details                               |
| --------------------------- | ------------- | ------------------------------------- |
| Data at Rest (raw-zone)     | AES-256 / KMS | Customer-managed key, 90-day rotation |
| Data at Rest (curated-zone) | AES-256 / SSE | Standard managed encryption           |
| Data in Transit             | TLS 1.3       | All inter-service communication       |
| PII (Application)           | SHA-256       | Irreversible cryptographic hash       |

---

## ☁ Cloud Deployment Mapping

Every local component maps to a managed cloud service:

| Local             | AWS                   | Azure                    | Advantage                |
| ----------------- | --------------------- | ------------------------ | ------------------------ |
| Redpanda          | Kinesis Data Streams  | Event Hubs               | Auto-scaling shards      |
| Python Generators | IoT Core + Rules      | IoT Hub                  | Managed device registry  |
| Governance Agent  | Lambda / ECS Fargate  | Functions / ACI          | Auto-scaling containers  |
| MinIO             | S3 + KMS              | Blob Storage + Key Vault | Unlimited, encrypted     |
| FastAPI           | API Gateway + Lambda  | API Management           | Serverless, rate-limited |
| Streamlit         | ECS + ALB             | Container Apps           | Managed hosting          |
| Prometheus        | CloudWatch Metrics    | Azure Monitor            | Managed collection       |
| Grafana           | CloudWatch Dashboards | Azure Dashboards         | No infrastructure        |

**Estimated cloud cost:** ~$114/month (AWS, moderate load)

---

## Project Structure

```
smart-city-platform/
├── docker-compose.yml              # 10-service orchestration
├── README.md                       # This file
├── report.tex                      # LaTeX report source
│
├── .github/
│   └── workflows/
│       └── pipeline-ci.yml         # CI/CD: test → build → integration
│
├── generators/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── traffic_generator.py        # Simulated traffic cameras (PII)
│   └── pollution_generator.py      # Simulated air quality sensors
│
├── governance/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── agent.py                    # PII governance agent (main)
│   └── test_governance.py          # 20 unit tests
│
├── analytics/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── query_service.py            # FastAPI (10 endpoints + metrics)
│
├── dashboard/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app.py                      # 5-page Streamlit dashboard
│
├── monitoring/
│   ├── prometheus.yml              # Prometheus scrape config
│   └── provisioning/
│       └── datasources/
│           └── datasource.yml      # Grafana auto-provisioning
│
├── security/
│   ├── setup_policies.py           # IAM policy simulation
│   └── load_test.py                # Throughput benchmark
│
└── screenshots/                    # Report figures
```

---

## Troubleshooting

### Containers won't start

```bash
# Check Docker is running
docker info

# Check for port conflicts
sudo lsof -i :8000 -i :8080 -i :8501 -i :9092

# Nuclear restart
docker compose down -v
docker compose up -d --build
```

### Governance agent shows no output

Python buffers stdout in Docker. The agent code includes `sys.stdout.reconfigure(line_buffering=True)` to fix this. If logs are still empty, wait 10 seconds — the agent needs Redpanda to be healthy first.

```bash
# Check if Redpanda is healthy
docker compose ps redpanda

# Check governance agent logs
docker logs --tail 30 governance-agent
```

### Dashboard shows 0 for PII metrics

The dashboard field names must match the API response exactly. Verify:

```bash
curl -s http://localhost:8000/api/v1/governance/stats | python3 -m json.tool
```

The field is `traffic_records_with_pii`. If the dashboard uses a different name, update `dashboard/app.py`.

### MinIO buckets are empty

The governance agent creates buckets automatically. If they're missing:

```bash
# Check if governance agent connected to MinIO
docker logs governance-agent | grep -i minio

# Restart the agent
docker compose restart governance-agent
```

### Python 3.14 local issues

The Docker containers use Python 3.11. Don't pip install locally — everything runs inside containers. If you need to run tests locally:

```bash
# Use Python 3.11 specifically
python3.11 -m venv venv
source venv/bin/activate
cd governance && python test_governance.py
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit changes (`git commit -m 'Add your feature'`)
4. Push to branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please ensure all 20 unit tests pass before submitting:

```bash
cd governance && python3 test_governance.py
```

---

<div align="center">

**Built with**

[![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

---
