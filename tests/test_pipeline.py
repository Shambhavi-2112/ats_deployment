import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from ats_pipeline import ATSPipeline
from api import app

@pytest.fixture(scope="module")
def pipeline():
    return ATSPipeline()

@pytest.fixture(scope="module")
def client():
    return TestClient(app)

class TestModelInvariants:
    def test_models_loaded(self, pipeline):
        assert pipeline.sarimax_model is not None
        assert pipeline.var_model is not None
        assert pipeline.garch_model is not None
        assert len(pipeline.delhi_history) > 1000
        assert len(pipeline.nifty_history) > 1000

    def test_pm25_forecast_mathematical_invariants(self, pipeline):
        res = pipeline.forecast_pm25(horizon_days=7, scenario="autonomous_var")
        records = res['forecast_records']
        
        assert len(records) == 7
        for r in records:
            # Physical concentration must be strictly positive
            assert r['pm25_forecast'] > 0.0
            # Lower CI <= Forecast <= Upper CI
            assert r['lower_ci'] <= r['pm25_forecast'] <= r['upper_ci']
            # Exogenous concentrations must be non-negative
            assert r['no2_level'] > 0.0
            assert r['so2_level'] > 0.0
            # AQI category must be standard
            assert r['aqi_category'] in ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]

    def test_exogenous_scenario_sensitivity(self, pipeline):
        res_var = pipeline.forecast_pm25(horizon_days=5, scenario="autonomous_var")
        res_winter = pipeline.forecast_pm25(horizon_days=5, scenario="winter_inversion")
        res_grap = pipeline.forecast_pm25(horizon_days=5, scenario="grap_intervention")
        
        # Winter inversion surge must yield higher PM2.5 than GRAP intervention
        assert res_winter['summary']['next_day_pm25'] > res_grap['summary']['next_day_pm25']
        # Winter surge should yield higher mean NO2 than GRAP
        assert res_winter['summary']['mean_no2'] > res_grap['summary']['mean_no2']

    def test_garch_volatility_mathematical_invariants(self, pipeline):
        res = pipeline.forecast_volatility(horizon_days=5)
        records = res['forecast_records']
        
        assert len(records) == 5
        # Covariance stationarity constraint: alpha + beta < 1
        alpha = pipeline.nifty_meta['alpha']
        beta = pipeline.nifty_meta['beta']
        assert (alpha + beta) < 1.0, f"GARCH non-stationary: alpha+beta={alpha+beta}"
        
        # Finite variance constraint: degrees of freedom nu > 2
        nu = pipeline.nifty_meta['degrees_freedom']
        assert nu > 2.0, f"Student-t degrees of freedom must exceed 2, got {nu}"
        
        for r in records:
            assert r['daily_vol_pct'] > 0.0
            assert r['annualized_vol_pct'] > 0.0
            # VaR 99% loss quantile must strictly exceed VaR 95%
            assert r['var_99_pct'] > r['var_95_pct']
            # Expected Shortfall (CVaR) must exceed VaR 95%
            assert r['cvar_95_pct'] >= r['var_95_pct']

class TestFastAPIEndpoints:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["models_loaded"]["sarimax"] is True
        assert data["models_loaded"]["var_exog"] is True
        assert data["models_loaded"]["garch"] is True

    def test_forecast_pm25_endpoint(self, client):
        payload = {
            "horizon_days": 5,
            "scenario": "autonomous_var",
            "confidence_level": 0.95
        }
        response = client.post("/forecast/pm25", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "forecast_records" in data
        assert len(data["forecast_records"]) == 5
        assert "summary" in data

    def test_forecast_volatility_endpoint(self, client):
        payload = {
            "horizon_days": 5,
            "confidence_level": 0.95
        }
        response = client.post("/forecast/volatility", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "forecast_records" in data
        assert len(data["forecast_records"]) == 5
        assert data["summary"]["degrees_of_freedom"] > 2.0
