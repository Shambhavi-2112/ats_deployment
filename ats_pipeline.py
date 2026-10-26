import os
import joblib
import numpy as np
import pandas as pd
from scipy import stats

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")

class ATSPipeline:
    def __init__(self):
        self._load_models()

    def _load_models(self):
        self.sarimax_model = joblib.load(os.path.join(MODELS_DIR, "delhi_pm25_sarimax_model.joblib"))
        self.var_model = joblib.load(os.path.join(MODELS_DIR, "delhi_exog_var_model.joblib"))
        self.delhi_meta = joblib.load(os.path.join(MODELS_DIR, "delhi_metadata.joblib"))
        self.delhi_history = pd.read_csv(os.path.join(MODELS_DIR, "delhi_history.csv"), index_col=0, parse_dates=True)

        self.garch_model = joblib.load(os.path.join(MODELS_DIR, "nifty_garch_model.joblib"))
        self.nifty_meta = joblib.load(os.path.join(MODELS_DIR, "nifty_metadata.joblib"))
        self.nifty_history = pd.read_csv(os.path.join(MODELS_DIR, "nifty_history.csv"), index_col=0, parse_dates=True)

    @staticmethod
    def classify_aqi(pm25_val: float) -> tuple[str, str, str]:
        """Classify PM2.5 concentration according to CPCB National Ambient Air Quality Standards."""
        if pm25_val <= 30:
            return "Good", "#2ecc71", "Minimal impact. Safe for outdoor physical activities."
        elif pm25_val <= 60:
            return "Satisfactory", "#27ae60", "Minor breathing discomfort to sensitive people."
        elif pm25_val <= 90:
            return "Moderate", "#f39c12", "Breathing discomfort to people with lungs, asthma, and heart diseases."
        elif pm25_val <= 120:
            return "Poor", "#e67e22", "Breathing discomfort to most people on prolonged exposure."
        elif pm25_val <= 250:
            return "Very Poor", "#e74c3c", "Respiratory illness on prolonged exposure. Pronounced effect on sensitive groups."
        else:
            return "Severe", "#8e44ad", "Health emergency: affects healthy people and seriously impacts those with existing diseases."

    def forecast_pm25(
        self,
        horizon_days: int = 7,
        scenario: str = "autonomous_var",
        custom_no2: float | None = None,
        custom_so2: float | None = None,
        confidence_level: float = 0.95
    ) -> dict:
        """
        Production SARIMAX forecasting pipeline with Vector Autoregression (VAR) exogenous projections.
        
        Scenarios:
        - 'autonomous_var': Dynamic multivariate VAR(p) forecast of NO2 and SO2
        - 'winter_inversion': Seasonal smog/stubble burning (+40% NO2, +25% SO2)
        - 'grap_intervention': Graded Response Action Plan policy controls (-30% NO2, -20% SO2)
        - 'custom': User-specified constant or scaled exogenous levels
        """
        horizon_days = max(1, min(30, int(horizon_days)))
        last_date = pd.to_datetime(self.delhi_meta['last_date'])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon_days, freq="D")

        # 1. Generate autonomous exogenous projections using VAR(p)
        k_ar = self.var_model.k_ar
        history_window = self.delhi_history[['NO2', 'SO2']].values[-k_ar:]
        var_forecast = self.var_model.forecast(y=history_window, steps=horizon_days)
        exog_df = pd.DataFrame(var_forecast, columns=['NO2', 'SO2'], index=future_dates)

        # 2. Apply scenario transformations
        scenario_description = ""
        if scenario == "autonomous_var":
            scenario_description = f"Autonomous VAR({k_ar}) multivariate dynamic projection."
        elif scenario == "winter_inversion":
            exog_df['NO2'] = exog_df['NO2'] * 1.40
            exog_df['SO2'] = exog_df['SO2'] * 1.25
            scenario_description = "Severe Winter Inversion / Stubble Surge (+40% NO2, +25% SO2)."
        elif scenario == "grap_intervention":
            exog_df['NO2'] = np.maximum(5.0, exog_df['NO2'] * 0.70)
            exog_df['SO2'] = np.maximum(2.0, exog_df['SO2'] * 0.80)
            scenario_description = "GRAP Anti-Pollution Emergency Interventions (-30% NO2, -20% SO2)."
        elif scenario == "custom":
            if custom_no2 is not None:
                exog_df['NO2'] = float(custom_no2)
            if custom_so2 is not None:
                exog_df['SO2'] = float(custom_so2)
            scenario_description = f"User Custom Exogenous Overrides (NO2={custom_no2}, SO2={custom_so2})."
        else:
            scenario_description = "Default autonomous projection."

        # 3. Generate SARIMAX forecasts
        alpha = 1.0 - confidence_level
        forecast_obj = self.sarimax_model.get_forecast(steps=horizon_days, exog=exog_df.values)
        pred_log_mean = np.asarray(forecast_obj.predicted_mean)
        conf_int_log = np.asarray(forecast_obj.conf_int(alpha=alpha))

        # 4. Inverse log transformation back to physical µg/m³
        pred_pm25 = np.exp(pred_log_mean)
        lower_bound = np.exp(conf_int_log[:, 0])
        upper_bound = np.exp(conf_int_log[:, 1])

        # 5. Assemble structured records
        records = []
        for i in range(horizon_days):
            cat_name, cat_color, advisory = self.classify_aqi(pred_pm25[i])
            records.append({
                'horizon_step': f"T+{i+1}",
                'date': future_dates[i].strftime("%Y-%m-%d"),
                'pm25_forecast': round(float(pred_pm25[i]), 2),
                'lower_ci': round(float(lower_bound[i]), 2),
                'upper_ci': round(float(upper_bound[i]), 2),
                'no2_level': round(float(exog_df['NO2'].iloc[i]), 2),
                'so2_level': round(float(exog_df['SO2'].iloc[i]), 2),
                'aqi_category': cat_name,
                'aqi_color': cat_color,
                'health_advisory': advisory
            })

        table_df = pd.DataFrame(records)

        next_cat, next_color, next_adv = self.classify_aqi(records[0]['pm25_forecast'])
        peak_idx = int(np.argmax(pred_pm25))

        return {
            'scenario': scenario,
            'scenario_description': scenario_description,
            'confidence_level': confidence_level,
            'horizon_days': horizon_days,
            'forecast_records': records,
            'summary': {
                'next_day_pm25': records[0]['pm25_forecast'],
                'next_day_aqi': next_cat,
                'next_day_color': next_color,
                'peak_pm25': round(float(pred_pm25[peak_idx]), 2),
                'peak_day': records[peak_idx]['horizon_step'],
                'mean_no2': round(float(exog_df['NO2'].mean()), 2),
                'mean_so2': round(float(exog_df['SO2'].mean()), 2),
                'model_name': 'SARIMAX(1,1,2)x(1,0,1,7) with VAR(14) Exogenous'
            }
        }

    def forecast_volatility(
        self,
        horizon_days: int = 5,
        confidence_level: float = 0.95
    ) -> dict:
        """
        Production GARCH(1,1) Volatility & Tail-Risk Forecasting Pipeline under Student's t Innovations.
        Computes conditional variance, annualized volatility, 1-day Value at Risk (VaR), and Expected Shortfall.
        """
        horizon_days = max(1, min(30, int(horizon_days)))
        last_date = pd.to_datetime(self.nifty_meta['last_date'])
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=horizon_days, freq="B")

        # 1. GARCH Multi-step analytical variance forecast
        garch_forecast = self.garch_model.forecast(horizon=horizon_days)
        cond_variance = garch_forecast.variance.iloc[-1].values[:horizon_days]
        daily_vol_pct = np.sqrt(cond_variance)
        annualized_vol_pct = daily_vol_pct * np.sqrt(252)

        # 2. Risk metrics with Student's t distribution
        nu = self.nifty_meta['degrees_freedom']
        mu = self.nifty_meta['mu']
        
        # Scaling factor for standardized Student-t
        std_scale = np.sqrt((nu - 2.0) / nu) if nu > 2 else 1.0

        records = []
        for i in range(horizon_days):
            sigma_d = daily_vol_pct[i]
            ann_v = annualized_vol_pct[i]

            # Parametric VaR (Loss exceeds VaR with probability 1 - alpha)
            t_crit_95 = stats.t.ppf(0.95, df=nu)
            t_crit_99 = stats.t.ppf(0.99, df=nu)

            var_95 = -(mu - t_crit_95 * sigma_d * std_scale)
            var_99 = -(mu - t_crit_99 * sigma_d * std_scale)

            # Expected Shortfall (CVaR) for Student's t
            pdf_val = stats.t.pdf(t_crit_95, df=nu)
            cvar_factor = (pdf_val / 0.05) * ((nu + t_crit_95**2) / (nu - 1.0))
            expected_shortfall = -(mu - cvar_factor * sigma_d * std_scale)

            # Volatility Regime
            if ann_v < 12.0:
                regime = "Low (Calm / Bullish Stability)"
                regime_color = "#2ecc71"
            elif ann_v < 18.0:
                regime = "Normal Market Volatility"
                regime_color = "#3498db"
            elif ann_v < 25.0:
                regime = "Elevated Risk Regime"
                regime_color = "#f39c12"
            else:
                regime = "High Volatility Stress"
                regime_color = "#e74c3c"

            records.append({
                'horizon_step': f"T+{i+1}",
                'date': future_dates[i].strftime("%Y-%m-%d") if i < len(future_dates) else f"T+{i+1}",
                'daily_vol_pct': round(float(sigma_d), 3),
                'annualized_vol_pct': round(float(ann_v), 2),
                'var_95_pct': round(float(var_95), 2),
                'var_99_pct': round(float(var_99), 2),
                'cvar_95_pct': round(float(expected_shortfall), 2),
                'regime': regime,
                'regime_color': regime_color
            })

        mean_ann = np.mean(annualized_vol_pct)
        if mean_ann < 12.0:
            overall_regime = "Low Volatility (Calm)"
            overall_color = "#2ecc71"
        elif mean_ann < 18.0:
            overall_regime = "Normal Volatility"
            overall_color = "#3498db"
        elif mean_ann < 25.0:
            overall_regime = "Elevated Uncertainty"
            overall_color = "#f39c12"
        else:
            overall_regime = "High Market Stress"
            overall_color = "#e74c3c"

        return {
            'horizon_days': horizon_days,
            'confidence_level': confidence_level,
            'forecast_records': records,
            'summary': {
                'next_day_daily_vol': records[0]['daily_vol_pct'],
                'next_day_ann_vol': records[0]['annualized_vol_pct'],
                'next_day_var_95': records[0]['var_95_pct'],
                'next_day_var_99': records[0]['var_99_pct'],
                'mean_ann_vol': round(float(mean_ann), 2),
                'overall_regime': overall_regime,
                'overall_color': overall_color,
                'unconditional_vol': round(float(self.nifty_meta['unconditional_vol'] * np.sqrt(252)), 2),
                'degrees_of_freedom': round(float(nu), 2),
                'model_name': "GARCH(1,1) with Standardized Student's t Innovations"
            }
        }
