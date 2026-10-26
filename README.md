# Applied Time Series Analysis & Production Deployment Package

**Authors:** Shambhavi Prasad (I057) & Saumya Prasad (I058) — Batch B2  
**Domain:** Applied Time Series Analysis (Dual-Domain: Environmental Air Quality & Financial Risk)

---

## 📁 Consolidated Project Directory Structure

```text
ats_deployment/
├── notebook_artifacts/
│   ├── I057_I058_ATS_Project.ipynb     # Original 16-step Jupyter Capstone Notebook
│   └── champion_sarimax_delhi.pkl      # Serialized champion SARIMAX model object
│
├── models/                             # Trained production models & historical data
│   ├── delhi_pm25_sarimax_model.joblib # Production SARIMAX(1,1,2)x(1,0,1,7) model
│   ├── delhi_exog_var_model.joblib     # Production Vector Autoregression VAR(14)
│   ├── nifty_garch_model.joblib        # GARCH(1,1) with Student's t innovations
│   ├── delhi_metadata.joblib           # Metadata & baseline metrics for Delhi
│   ├── nifty_metadata.joblib           # Metadata & parameters for NIFTY 50
│   ├── delhi_history.csv               # Historical daily air quality series
│   └── nifty_history.csv               # Historical daily financial returns series
│
├── ats_pipeline.py                     # Production Python inference engine & scenario manager
├── api.py                              # FastAPI production REST API (Swagger at /docs)
├── app.py                              # Interactive Streamlit dashboard with Plotly
├── prepare_models.py                   # Automated retraining & artifact serialization pipeline
│
├── tests/
│   └── test_pipeline.py                # Pytest suite (invariants, sensitivity, and API contracts)
│
├── Jenkinsfile                         # Declarative 8-stage Jenkins CI/CD pipeline
├── Dockerfile                          # Container specification (Python 3.11-slim)
├── docker-compose.yml                  # Production multi-service orchestration
├── entrypoint.sh                       # Startup script for FastAPI + Streamlit
└── requirements.txt                    # Pinned Python package dependencies
```

---

## 🚀 Quickstart Guide

### 1. Run the Interactive Streamlit Dashboard
```bash
streamlit run app.py --server.port 8501
```
Open your browser at `http://localhost:8501` to access:
- **Tab 1: Environmental Air Quality:** Autonomous $\text{VAR}$ projections, interactive $\text{PM}_{2.5}$ fan chart, and CPCB health advisories.
- **Tab 2: Financial Volatility (NIFTY 50):** $\text{GARCH}(1,1)$ volatility fan chart and Student's $t$ ($\nu = 6.38$) Value at Risk ($\text{VaR}$).
- **Tab 3: Exogenous Scenario Comparison:** Compare Autonomous VAR vs. Winter Smog Surge vs. GRAP Policy Interventions.
- **Tab 4: Theoretical Architecture:** Academic justification comparing Box-Jenkins vs. Econometric Volatility models.
- **Tab 5: REST API & Integration:** Live API payloads and integration examples.

### 2. Run the FastAPI Production Backend
```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: `http://localhost:8000/docs`
- Health check: `curl http://localhost:8000/health`

### 3. Run the Automated Test Suite (Pytest)
```bash
PYTHONPATH=. pytest tests/test_pipeline.py -v
```
All 7 unit, mathematical invariant, and API integration tests pass with 100% success.

### 4. Build and Run with Docker
```bash
docker compose up -d --build
```
This launches both FastAPI on port 8000 and Streamlit on port 8501 inside an isolated container.

### 5. Automated CI/CD with Jenkins
The included [`Jenkinsfile`](Jenkinsfile) defines an 8-stage pipeline:
1. Environment Setup & Dependency Installation
2. Static Code Analysis (`flake8`)
3. Model Invariant & Artifact Validation
4. Automated Test Suite (`pytest` with JUnit XML)
5. Docker Container Image Build
6. Ephemeral Smoke Test & Healthcheck Verification
7. Container Registry Push
8. Zero-Downtime Deployment
