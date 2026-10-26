import os
import joblib
import numpy as np
import pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.api import VAR
from arch import arch_model
import yfinance as yf

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "models")
os.makedirs(MODELS_DIR, exist_ok=True)

print("1. Extracting historical environmental data from champion model...")
pkl_path = "/Users/saumya_shambhavi/Downloads/champion_sarimax_delhi.pkl"
if not os.path.exists(pkl_path):
    raise FileNotFoundError(f"Missing {pkl_path}")

sarimax_ref = joblib.load(pkl_path)
n_obs = sarimax_ref.model.endog.shape[0]
dates = pd.date_range(start="2015-01-01", periods=n_obs, freq="D")

delhi_df = pd.DataFrame({
    'PM2.5': np.exp(sarimax_ref.model.endog.flatten()),
    'log_pm25': sarimax_ref.model.endog.flatten(),
    'NO2': sarimax_ref.model.exog[:, 0],
    'SO2': sarimax_ref.model.exog[:, 1]
}, index=dates)

print(f"Delhi series recovered: {len(delhi_df)} observations ({dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d})")

# Save recent historical series for dashboard visualization
delhi_df.to_csv(os.path.join(MODELS_DIR, "delhi_history.csv"))
recent_delhi = delhi_df.iloc[-90:].copy()
recent_delhi.to_csv(os.path.join(MODELS_DIR, "recent_delhi.csv"))

# Save the production SARIMAX model
joblib.dump(sarimax_ref, os.path.join(MODELS_DIR, "delhi_pm25_sarimax_model.joblib"))
print("Saved delhi_pm25_sarimax_model.joblib")

# Fit Vector Autoregression (VAR) on Exogenous Variables [NO2, SO2]
print("2. Fitting Vector Autoregression (VAR) on Exogenous Variables [NO2, SO2]...")
exog_data = delhi_df[['NO2', 'SO2']].copy()
var_estimator = VAR(exog_data)
lag_order_results = var_estimator.select_order(maxlags=14)
best_p = max(1, lag_order_results.selected_orders.get('aic', 7))
print(f"Optimal VAR lag order selected by AIC: p = {best_p}")

var_model = var_estimator.fit(best_p)
joblib.dump(var_model, os.path.join(MODELS_DIR, "delhi_exog_var_model.joblib"))

delhi_metadata = {
    'start_date': str(dates[0]),
    'last_date': str(dates[-1]),
    'n_obs': int(n_obs),
    'last_values': exog_data.iloc[-best_p:].to_dict(orient='records'),
    'means': exog_data.mean().to_dict(),
    'stds': exog_data.std().to_dict(),
    'q25': exog_data.quantile(0.25).to_dict(),
    'q75': exog_data.quantile(0.75).to_dict(),
    'last_pm25': float(delhi_df['PM2.5'].iloc[-1]),
    'last_log_pm25': float(delhi_df['log_pm25'].iloc[-1]),
    'var_order': int(best_p),
    'sarimax_order': (1, 1, 2),
    'sarimax_seasonal_order': (1, 0, 1, 7)
}
joblib.dump(delhi_metadata, os.path.join(MODELS_DIR, "delhi_metadata.joblib"))
print("Saved delhi_exog_var_model.joblib and delhi_metadata.joblib")

print("3. Fetching NIFTY 50 Financial Data & Fitting GARCH(1,1)-Student-t...")
nifty_raw = yf.download('^NSEI', start='2015-01-01', end='2025-01-01', auto_adjust=True, progress=False)
close_series = nifty_raw['Close']
if isinstance(close_series, pd.DataFrame):
    close_series = close_series.iloc[:, 0]

nifty = close_series.rename('close').to_frame()
nifty['return_pct'] = 100 * np.log(nifty['close'] / nifty['close'].shift(1))
nifty = nifty.dropna()

nifty.to_csv(os.path.join(MODELS_DIR, "nifty_history.csv"))
recent_nifty = nifty.iloc[-90:].copy()
recent_nifty.to_csv(os.path.join(MODELS_DIR, "recent_nifty.csv"))

garch_model = arch_model(
    nifty['return_pct'],
    mean='Constant',
    vol='GARCH',
    p=1, q=1,
    dist='t',
    rescale=False
).fit(disp='off')

joblib.dump(garch_model, os.path.join(MODELS_DIR, "nifty_garch_model.joblib"))

nifty_metadata = {
    'start_date': str(nifty.index.min()),
    'last_date': str(nifty.index.max()),
    'n_obs': len(nifty),
    'last_close': float(nifty['close'].iloc[-1]),
    'last_return': float(nifty['return_pct'].iloc[-1]),
    'unconditional_vol': float(nifty['return_pct'].std()),
    'degrees_freedom': float(garch_model.params.get('nu', 6.38)),
    'omega': float(garch_model.params.get('omega', 0.028)),
    'alpha': float(garch_model.params.get('alpha[1]', 0.081)),
    'beta': float(garch_model.params.get('beta[1]', 0.886)),
    'mu': float(garch_model.params.get('mu', 0.083))
}
joblib.dump(nifty_metadata, os.path.join(MODELS_DIR, "nifty_metadata.joblib"))
print("Saved nifty_garch_model.joblib and nifty_metadata.joblib")

print("\nAll models and metadata successfully prepared and saved to disk.")
