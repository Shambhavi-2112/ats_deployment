import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from ats_pipeline import ATSPipeline

app = FastAPI(
    title="Applied Time Series Production Inference API",
    description="Dual-Domain Forecasting API: Autonomous SARIMAX + VAR for Environmental PM2.5 and GARCH(1,1)-t for NIFTY 50 Volatility.",
    version="1.0.0"
)

# Enable CORS for external dashboard or client integrations
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize pipeline once in memory
pipeline = ATSPipeline()

# Pydantic Schemas
class PM25ForecastRequest(BaseModel):
    horizon_days: int = Field(default=7, ge=1, le=30, description="Forecast horizon in days (1 to 30).")
    scenario: str = Field(
        default="autonomous_var",
        description="Exogenous scenario: 'autonomous_var', 'winter_inversion', 'grap_intervention', 'custom'."
    )
    custom_no2: Optional[float] = Field(default=None, description="Custom NO2 level (µg/m³) if scenario is 'custom'.")
    custom_so2: Optional[float] = Field(default=None, description="Custom SO2 level (µg/m³) if scenario is 'custom'.")
    confidence_level: float = Field(default=0.95, ge=0.50, le=0.99, description="Confidence interval coverage (0.50 to 0.99).")

class VolatilityForecastRequest(BaseModel):
    horizon_days: int = Field(default=5, ge=1, le=30, description="Forecast horizon in days (1 to 30).")
    confidence_level: float = Field(default=0.95, ge=0.50, le=0.99, description="Confidence coverage for Value at Risk.")

@app.get("/", tags=["System"])
def root():
    return {
        "service": "Applied Time Series Production Engine",
        "status": "online",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "models_summary": "/models/summary",
            "scenarios_list": "/scenarios/list",
            "forecast_pm25": "POST /forecast/pm25",
            "forecast_volatility": "POST /forecast/volatility"
        }
    }

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "models_loaded": {
            "sarimax": pipeline.sarimax_model is not None,
            "var_exog": pipeline.var_model is not None,
            "garch": pipeline.garch_model is not None
        },
        "delhi_historical_obs": pipeline.delhi_meta.get("n_obs"),
        "nifty_historical_obs": pipeline.nifty_meta.get("n_obs")
    }

@app.get("/scenarios/list", tags=["Scenarios"])
def list_scenarios():
    return {
        "scenarios": [
            {
                "id": "autonomous_var",
                "name": "Autonomous VAR Multi-Step Forecast",
                "description": "Dynamic multi-step projection of NO2 and SO2 via empirical Vector Autoregression (VAR) without human intervention."
            },
            {
                "id": "winter_inversion",
                "name": "Winter Stubble / Temperature Inversion Surge",
                "description": "Simulates seasonal atmospheric trapping with +40% NO2 and +25% SO2 surges above baseline."
            },
            {
                "id": "grap_intervention",
                "name": "GRAP Emergency Emission Restrictions",
                "description": "Simulates anti-pollution policy enforcement with -30% NO2 and -20% SO2 reductions."
            },
            {
                "id": "custom",
                "name": "Manual Covariate Override",
                "description": "User sets static custom levels for NO2 and SO2."
            }
        ]
    }

@app.get("/models/summary", tags=["Models"])
def models_summary():
    return {
        "environmental_model": {
            "target": "Delhi Daily PM2.5 Concentration (µg/m³)",
            "specification": "SARIMAX(1,1,2) x (1,0,1)[7] with Log Transform",
            "exogenous_engine": f"Vector Autoregression VAR({pipeline.var_model.k_ar}) on [NO2, SO2]",
            "training_span": f"{pipeline.delhi_meta['start_date']} to {pipeline.delhi_meta['last_date']}",
            "historical_observations": pipeline.delhi_meta['n_obs'],
            "aic": round(float(pipeline.sarimax_model.aic), 2),
            "bic": round(float(pipeline.sarimax_model.bic), 2)
        },
        "financial_model": {
            "target": "NIFTY 50 Daily Percentage Log Returns (%)",
            "specification": "GARCH(1,1) with Standardized Student's t Innovations",
            "training_span": f"{pipeline.nifty_meta['start_date']} to {pipeline.nifty_meta['last_date']}",
            "historical_observations": pipeline.nifty_meta['n_obs'],
            "degrees_of_freedom": round(float(pipeline.nifty_meta['degrees_freedom']), 2),
            "omega": round(float(pipeline.nifty_meta['omega']), 4),
            "alpha": round(float(pipeline.nifty_meta['alpha']), 4),
            "beta": round(float(pipeline.nifty_meta['beta']), 4),
            "persistence_alpha_plus_beta": round(float(pipeline.nifty_meta['alpha'] + pipeline.nifty_meta['beta']), 4),
            "aic": round(float(pipeline.garch_model.aic), 2),
            "bic": round(float(pipeline.garch_model.bic), 2)
        }
    }

@app.post("/forecast/pm25", tags=["Forecasting"])
def forecast_pm25_endpoint(request: PM25ForecastRequest):
    try:
        result = pipeline.forecast_pm25(
            horizon_days=request.horizon_days,
            scenario=request.scenario,
            custom_no2=request.custom_no2,
            custom_so2=request.custom_so2,
            confidence_level=request.confidence_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forecast/volatility", tags=["Forecasting"])
def forecast_volatility_endpoint(request: VolatilityForecastRequest):
    try:
        result = pipeline.forecast_volatility(
            horizon_days=request.horizon_days,
            confidence_level=request.confidence_level
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
