import os
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats
from ats_pipeline import ATSPipeline

st.set_page_config(
    page_title="ATS Production Intelligence: PM2.5 & Volatility",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (Glassmorphism & Sleek Dark Mode)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        padding: 24px 32px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
        margin-bottom: 24px;
    }
    
    .metric-card {
        background: rgba(30, 41, 59, 0.7);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 18px 20px;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.3);
    }
    .metric-title {
        color: #94a3b8;
        font-size: 0.85rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 6px;
    }
    .metric-value {
        color: #f8fafc;
        font-size: 1.85rem;
        font-weight: 700;
        line-height: 1.2;
    }
    .metric-sub {
        font-size: 0.8rem;
        margin-top: 6px;
        display: flex;
        align-items: center;
        gap: 6px;
    }
    
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.03em;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_pipeline():
    return ATSPipeline()

pipeline = get_pipeline()

# Header Banner
st.markdown("""
<div class="main-header">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
        <div>
            <h1 style="margin: 0; font-size: 1.9rem; font-weight: 800; color: #ffffff; letter-spacing: -0.02em;">
                ⚡ Applied Time Series Production Engine
            </h1>
            <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.95rem;">
                Dual-Domain Inference: Autonomous SARIMAX + VAR (Delhi Air Quality) & GARCH(1,1)-t (NIFTY 50 Volatility)
            </p>
        </div>
        <div style="text-align: right;">
            <span class="badge" style="background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.4);">
                ● Production Engine Active
            </span>
            <div style="color: #94a3b8; font-size: 0.75rem; margin-top: 4px;">
                Models: SARIMAX(1,1,2)x(1,0,1,7) & GARCH(1,1)-t
            </div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# Tabs
tab_env, tab_fin, tab_scenarios, tab_theory, tab_api = st.tabs([
    "🌿 Environmental Air Quality (PM2.5)",
    "📈 Financial Volatility (NIFTY 50)",
    "🧪 Exogenous Scenario Comparison",
    "📚 Theoretical Architecture & Model Cards",
    "🔌 REST API & Integration"
])

# ==============================================================================
# TAB 1: ENVIRONMENTAL AIR QUALITY
# ==============================================================================
with tab_env:
    col_ctrl, col_main = st.columns([1, 3])
    
    with col_ctrl:
        st.markdown("### 🎛️ Forecast Controls")
        
        horizon = st.slider(
            "Forecast Horizon (Days)",
            min_value=1, max_value=30, value=14, step=1,
            help="Number of days forward to project PM2.5."
        )
        
        confidence = st.select_slider(
            "Confidence Interval Coverage",
            options=[0.80, 0.90, 0.95, 0.99],
            value=0.95,
            format_func=lambda x: f"{int(x*100)}% Confidence Interval"
        )
        
        scenario = st.selectbox(
            "Exogenous Simulation Mode",
            options=["autonomous_var", "winter_inversion", "grap_intervention", "custom"],
            format_func=lambda x: {
                "autonomous_var": "🤖 Autonomous VAR (Empirical Dynamic)",
                "winter_inversion": "🔥 Winter Smog / Stubble Surge (+40% NO2, +25% SO2)",
                "grap_intervention": "🛡️ GRAP Emergency Controls (-30% NO2, -20% SO2)",
                "custom": "⚙️ Manual Covariate Override"
            }[x],
            help="Controls how future NO2 and SO2 levels are estimated."
        )
        
        custom_no2, custom_so2 = None, None
        if scenario == "custom":
            st.markdown("#### Custom Exogenous Inputs")
            custom_no2 = st.slider("Expected NO2 (µg/m³)", 5.0, 150.0, 40.0, 1.0)
            custom_so2 = st.slider("Expected SO2 (µg/m³)", 2.0, 50.0, 10.0, 0.5)
            
        st.info(
            "💡 **Autonomous VAR Engine:** When selected, future NO2 and SO2 are projected via a Vector Autoregressive model trained on cross-pollutant interactions."
        )

    # Run inference
    res_pm = pipeline.forecast_pm25(
        horizon_days=horizon,
        scenario=scenario,
        custom_no2=custom_no2,
        custom_so2=custom_so2,
        confidence_level=confidence
    )
    
    df_fc = pd.DataFrame(res_pm['forecast_records'])
    summary = res_pm['summary']
    
    with col_main:
        # Top KPI Metrics
        k1, k2, k3, k4 = st.columns(4)
        
        with k1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Next-Day PM2.5</div>
                <div class="metric-value">{summary['next_day_pm25']} <span style="font-size: 1rem; color: #94a3b8;">µg/m³</span></div>
                <div class="metric-sub">
                    <span class="badge" style="background: {summary['next_day_color']}33; color: {summary['next_day_color']}; border: 1px solid {summary['next_day_color']};">
                        AQI: {summary['next_day_aqi']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with k2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Horizon Peak PM2.5</div>
                <div class="metric-value">{summary['peak_pm25']} <span style="font-size: 1rem; color: #94a3b8;">µg/m³</span></div>
                <div class="metric-sub" style="color: #94a3b8;">
                    Peak Expected on <strong>{summary['peak_day']}</strong>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with k3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Mean Projected NO2</div>
                <div class="metric-value">{summary['mean_no2']} <span style="font-size: 1rem; color: #94a3b8;">µg/m³</span></div>
                <div class="metric-sub" style="color: #38bdf8;">
                    Coupled VAR Regressor
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with k4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Mean Projected SO2</div>
                <div class="metric-value">{summary['mean_so2']} <span style="font-size: 1rem; color: #94a3b8;">µg/m³</span></div>
                <div class="metric-sub" style="color: #f59e0b;">
                    Industrial Tracer
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

        # Plotly Main PM2.5 Forecast Chart
        hist_df = pipeline.delhi_history.iloc[-60:].copy()
        
        fig = go.Figure()
        
        # Historical PM2.5
        fig.add_trace(go.Scatter(
            x=hist_df.index,
            y=hist_df['PM2.5'],
            mode='lines',
            name='Historical PM2.5 (Observed)',
            line=dict(color='#60a5fa', width=2),
            hovertemplate='<b>Date:</b> %{x|%Y-%m-%d}<br><b>PM2.5:</b> %{y:.1f} µg/m³<extra></extra>'
        ))
        
        # Confidence Ribbon
        fc_dates = pd.to_datetime(df_fc['date'])
        fig.add_trace(go.Scatter(
            x=list(fc_dates) + list(fc_dates[::-1]),
            y=list(df_fc['upper_ci']) + list(df_fc['lower_ci'][::-1]),
            fill='toself',
            fillcolor='rgba(139, 92, 246, 0.18)',
            line=dict(color='rgba(255,255,255,0)'),
            name=f'{int(confidence*100)}% Confidence Interval',
            hoverinfo='skip'
        ))
        
        # Point Forecast
        fig.add_trace(go.Scatter(
            x=fc_dates,
            y=df_fc['pm25_forecast'],
            mode='lines+markers',
            name='Point Forecast (SARIMAX)',
            line=dict(color='#a855f7', width=3),
            marker=dict(size=6, color='#c084fc', symbol='circle'),
            hovertemplate='<b>Horizon:</b> %{text}<br><b>Date:</b> %{x|%Y-%m-%d}<br><b>Predicted:</b> %{y:.1f} µg/m³<extra></extra>',
            text=df_fc['horizon_step']
        ))
        
        # National Ambient Standard Line (60 µg/m³)
        fig.add_hline(
            y=60, line_dash='dash', line_color='#ef4444', line_width=1.5,
            annotation_text="NAAQS Standard Limit (60 µg/m³)",
            annotation_position="top left",
            annotation_font=dict(color="#ef4444", size=10)
        )
        
        # Severe Threshold Line (250 µg/m³)
        fig.add_hline(
            y=250, line_dash='dot', line_color='#dc2626', line_width=1.5,
            annotation_text="Severe Hazard Threshold (250 µg/m³)",
            annotation_position="top left",
            annotation_font=dict(color="#dc2626", size=10)
        )

        fig.update_layout(
            title=dict(
                text=f"<b>Delhi Daily PM2.5 Trajectory & Autonomous Multi-Step Forecast</b> ({res_pm['scenario_description']})",
                font=dict(size=15, color="#f8fafc")
            ),
            xaxis=dict(title="Calendar Date", gridcolor="rgba(255,255,255,0.06)", showgrid=True),
            yaxis=dict(title="PM2.5 Concentration (µg/m³)", gridcolor="rgba(255,255,255,0.06)", showgrid=True),
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=430
        )
        st.plotly_chart(fig, use_container_width=True)

        # Exogenous Variables Projection Plot
        fig_exog = go.Figure()
        fig_exog.add_trace(go.Scatter(
            x=fc_dates, y=df_fc['no2_level'],
            mode='lines+markers', name='NO2 Exogenous Path (µg/m³)',
            line=dict(color='#38bdf8', width=2),
            marker=dict(size=5)
        ))
        fig_exog.add_trace(go.Scatter(
            x=fc_dates, y=df_fc['so2_level'],
            mode='lines+markers', name='SO2 Exogenous Path (µg/m³)',
            line=dict(color='#f59e0b', width=2),
            marker=dict(size=5)
        ))
        fig_exog.update_layout(
            title=dict(text="<b>Autonomous Exogenous Covariate Trajectories (VAR Projected)</b>", font=dict(size=14, color="#f8fafc")),
            xaxis=dict(title="Date", gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(title="Concentration (µg/m³)", gridcolor="rgba(255,255,255,0.05)"),
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=50, b=40),
            height=260
        )
        st.plotly_chart(fig_exog, use_container_width=True)

    # Detailed Forecast Table
    st.markdown("### 📋 Calibrated Forecast Records & Health Advisories")
    display_cols = ['horizon_step', 'date', 'pm25_forecast', 'lower_ci', 'upper_ci', 'no2_level', 'so2_level', 'aqi_category', 'health_advisory']
    rename_dict = {
        'horizon_step': 'Horizon',
        'date': 'Forecast Date',
        'pm25_forecast': 'PM2.5 (µg/m³)',
        'lower_ci': f'Lower {int(confidence*100)}% CI',
        'upper_ci': f'Upper {int(confidence*100)}% CI',
        'no2_level': 'NO2 Level',
        'so2_level': 'SO2 Level',
        'aqi_category': 'AQI Category',
        'health_advisory': 'CPCB Health Advisory'
    }
    st.dataframe(df_fc[display_cols].rename(columns=rename_dict), use_container_width=True)
    
    csv_data = df_fc[display_cols].to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download PM2.5 Forecast (CSV)",
        data=csv_data,
        file_name=f"delhi_pm25_forecast_{scenario}_{horizon}d.csv",
        mime="text/csv"
    )

# ==============================================================================
# TAB 2: FINANCIAL VOLATILITY (NIFTY 50)
# ==============================================================================
with tab_fin:
    f_col_ctrl, f_col_main = st.columns([1, 3])
    
    with f_col_ctrl:
        st.markdown("### 🎛️ Volatility Controls")
        
        vol_horizon = st.slider(
            "Forecast Horizon (Trading Days)",
            min_value=1, max_value=30, value=10, step=1,
            help="Number of trading sessions forward to project volatility."
        )
        
        var_confidence = st.selectbox(
            "Value at Risk (VaR) Confidence",
            options=[0.95, 0.99],
            format_func=lambda x: f"{int(x*100)}% Confidence Level",
            index=0
        )
        
        st.info(
            "📈 **Student's t Tail Modeling:** Financial return shocks exhibit high leptokurtosis (fat tails). The model applies standardized Student's t distribution (ν = 6.38) for exact risk quantification."
        )
        
    res_vol = pipeline.forecast_volatility(horizon_days=vol_horizon, confidence_level=var_confidence)
    df_vol = pd.DataFrame(res_vol['forecast_records'])
    v_summary = res_vol['summary']
    
    with f_col_main:
        vk1, vk2, vk3, vk4 = st.columns(4)
        
        with vk1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Daily Conditional Vol (T+1)</div>
                <div class="metric-value">{v_summary['next_day_daily_vol']}%</div>
                <div class="metric-sub" style="color: #94a3b8;">
                    Std Dev per Trading Day
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with vk2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Annualized Volatility</div>
                <div class="metric-value">{v_summary['next_day_ann_vol']}%</div>
                <div class="metric-sub">
                    <span class="badge" style="background: {v_summary['overall_color']}33; color: {v_summary['overall_color']}; border: 1px solid {v_summary['overall_color']};">
                        {v_summary['overall_regime']}
                    </span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with vk3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">1-Day VaR (95%)</div>
                <div class="metric-value">{v_summary['next_day_var_95']}%</div>
                <div class="metric-sub" style="color: #f87171;">
                    Max 1-Day Loss @ 95% Confidence
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        with vk4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">Student's t ν (Tail Fatness)</div>
                <div class="metric-value">{v_summary['degrees_of_freedom']}</div>
                <div class="metric-sub" style="color: #a78bfa;">
                    Heavy Tails (Normal = ∞)
                </div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)
        
        # Volatility Fan Chart
        fig_vol = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=(
            "<b>GARCH(1,1) Annualized Volatility Path vs Unconditional Benchmark</b>",
            "<b>1-Day Value at Risk (VaR) & Expected Shortfall (CVaR)</b>"
        ))
        
        h_labels = df_vol['horizon_step']
        
        # Annualized Vol
        fig_vol.add_trace(go.Scatter(
            x=h_labels, y=df_vol['annualized_vol_pct'],
            mode='lines+markers', name='Forecasted Annualized Volatility (%)',
            line=dict(color='#06b6d4', width=3),
            marker=dict(size=7, color='#22d3ee')
        ), row=1, col=1)
        
        fig_vol.add_hline(
            y=v_summary['unconditional_vol'], line_dash='dash', line_color='#94a3b8',
            annotation_text=f"Unconditional Long-Run Volatility ({v_summary['unconditional_vol']}%)",
            annotation_position="top right", row=1, col=1
        )
        
        # VaR and CVaR
        fig_vol.add_trace(go.Bar(
            x=h_labels, y=df_vol['var_95_pct'], name='1-Day VaR (95%)',
            marker_color='rgba(239, 68, 68, 0.7)'
        ), row=2, col=1)
        
        fig_vol.add_trace(go.Bar(
            x=h_labels, y=df_vol['cvar_95_pct'], name='Expected Shortfall (CVaR 95%)',
            marker_color='rgba(185, 28, 28, 0.9)'
        ), row=2, col=1)
        
        fig_vol.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(15, 23, 42, 0.6)",
            plot_bgcolor="rgba(15, 23, 42, 0.6)",
            legend=dict(orientation="h", yanchor="bottom", y=1.04, xanchor="right", x=1),
            margin=dict(l=40, r=40, t=60, b=40),
            height=460
        )
        fig_vol.update_yaxes(title_text="Annualized Vol (%)", row=1, col=1, gridcolor="rgba(255,255,255,0.05)")
        fig_vol.update_yaxes(title_text="Potential Loss (%)", row=2, col=1, gridcolor="rgba(255,255,255,0.05)")
        
        st.plotly_chart(fig_vol, use_container_width=True)

    st.markdown("### 📋 Calibrated Volatility & Risk Schedule")
    v_cols = ['horizon_step', 'date', 'daily_vol_pct', 'annualized_vol_pct', 'var_95_pct', 'var_99_pct', 'cvar_95_pct', 'regime']
    v_rename = {
        'horizon_step': 'Horizon',
        'date': 'Trading Session',
        'daily_vol_pct': 'Daily Volatility (%)',
        'annualized_vol_pct': 'Annualized Vol (%)',
        'var_95_pct': '1-Day VaR (95%)',
        'var_99_pct': '1-Day VaR (99%)',
        'cvar_95_pct': 'Expected Shortfall (95%)',
        'regime': 'Market Volatility Regime'
    }
    st.dataframe(df_vol[v_cols].rename(columns=v_rename), use_container_width=True)

# ==============================================================================
# TAB 3: EXOGENOUS SCENARIO COMPARISON
# ==============================================================================
with tab_scenarios:
    st.markdown("### 🧪 Cross-Scenario Environmental Sensitivity Analysis")
    st.markdown(
        "Demonstrating how atmospheric and policy interventions alter the projected $\\text{PM}_{2.5}$ trajectory across identical forecast horizons:"
    )
    
    scen_h = st.slider("Comparison Horizon (Days)", 7, 21, 14, key="scen_h")
    
    # Run 3 core scenarios
    res_base = pipeline.forecast_pm25(horizon_days=scen_h, scenario="autonomous_var")
    res_winter = pipeline.forecast_pm25(horizon_days=scen_h, scenario="winter_inversion")
    res_grap = pipeline.forecast_pm25(horizon_days=scen_h, scenario="grap_intervention")
    
    df_base = pd.DataFrame(res_base['forecast_records'])
    df_winter = pd.DataFrame(res_winter['forecast_records'])
    df_grap = pd.DataFrame(res_grap['forecast_records'])
    
    fig_cmp = go.Figure()
    
    fig_cmp.add_trace(go.Scatter(
        x=df_base['horizon_step'], y=df_base['pm25_forecast'],
        mode='lines+markers', name='🤖 Autonomous VAR Baseline',
        line=dict(color='#38bdf8', width=3),
        marker=dict(size=6)
    ))
    
    fig_cmp.add_trace(go.Scatter(
        x=df_winter['horizon_step'], y=df_winter['pm25_forecast'],
        mode='lines+markers', name='🔥 Winter Inversion (+40% NO2, +25% SO2)',
        line=dict(color='#f87171', width=3, dash='dash'),
        marker=dict(size=6)
    ))
    
    fig_cmp.add_trace(go.Scatter(
        x=df_grap['horizon_step'], y=df_grap['pm25_forecast'],
        mode='lines+markers', name='🛡️ GRAP Policy Controls (-30% NO2, -20% SO2)',
        line=dict(color='#34d399', width=3, dash='dot'),
        marker=dict(size=6)
    ))
    
    fig_cmp.add_hline(y=60, line_dash='dash', line_color='white', line_width=1, annotation_text="Standard (60 µg/m³)")
    
    fig_cmp.update_layout(
        title="<b>Multi-Scenario Comparative PM2.5 Trajectories</b>",
        xaxis=dict(title="Forecast Horizon Step", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(title="PM2.5 (µg/m³)", gridcolor="rgba(255,255,255,0.05)"),
        template="plotly_dark",
        paper_bgcolor="rgba(15, 23, 42, 0.6)",
        plot_bgcolor="rgba(15, 23, 42, 0.6)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=450
    )
    st.plotly_chart(fig_cmp, use_container_width=True)
    
    sc_col1, sc_col2, sc_col3 = st.columns(3)
    with sc_col1:
        st.markdown(f"**Autonomous VAR:** Next-day {res_base['summary']['next_day_pm25']} µg/m³ | Mean NO2: {res_base['summary']['mean_no2']} µg/m³")
    with sc_col2:
        st.markdown(f"**Winter Surge:** Next-day {res_winter['summary']['next_day_pm25']} µg/m³ | Peak: {res_winter['summary']['peak_pm25']} µg/m³")
    with sc_col3:
        st.markdown(f"**GRAP Controls:** Next-day {res_grap['summary']['next_day_pm25']} µg/m³ | Benefit: -{round(res_base['summary']['next_day_pm25'] - res_grap['summary']['next_day_pm25'], 2)} µg/m³")

# ==============================================================================
# TAB 4: THEORETICAL ARCHITECTURE & MODEL CARDS
# ==============================================================================
with tab_theory:
    st.markdown("### 📚 Theoretical Foundations & Domain-Model Alignment")
    
    st.markdown("""
    #### 1. Why Environmental Data is Suited for Box-Jenkins & SARIMAX
    - **Physical Inertia:** Atmospheric particulate concentration exhibits high conditional mean auto-persistence ($I(1)$ levels, $I(0)$ first-differences).
    - **Physical Covariates:** Chemical combustion processes produce co-pollutants ($\text{NO}_2, \text{SO}_2, \text{CO}$) whose atmospheric residence times directly correlate with $\text{PM}_{2.5}$.
    - **Atmospheric Seasonality:** Delhi experiences severe winter thermal inversions and summer monsoon washouts ($s=365$ annual, $s=7$ intra-week cycles).
    
    $$\\Phi_P(B^s)\\phi_p(B)(1-B)^d(1-B^s)^D \\ln(Y_t) = \\boldsymbol{\\beta}^\\top \\mathbf{X}_t + \\Theta_Q(B^s)\\theta_q(B)\\epsilon_t$$
    
    ---
    
    #### 2. Why Financial Returns Require Second-Moment Econometric Volatility (ARCH/GARCH)
    - **Weak Efficient Market Hypothesis:** Raw returns $r_t$ exhibit zero linear autocorrelation (ACF $\\approx 0$), rendering AR/MA models ineffective for mean directional prediction.
    - **Mandelbrot's Volatility Clustering:** Large price swings are followed by large swings, and small swings by small swings. Squared returns $r_t^2$ exhibit massive autocorrelation ($p < 10^{-80}$ via Engle's ARCH-LM test).
    - **Heavy Tails & Extreme Leptokurtosis:** Excess kurtosis in asset returns violates Gaussian assumptions, requiring standardized Student's $t$ innovations with parameter $\\nu$.
    
    $$\\sigma_t^2 = \\omega + \\sum_{i=1}^q \\alpha_i \\epsilon_{t-i}^2 + \\sum_{j=1}^p \\beta_j \\sigma_{t-j}^2, \\quad \\epsilon_t = \\sigma_t z_t, \\quad z_t \\sim t_\\nu(0, 1)$$
    """)

# ==============================================================================
# TAB 5: REST API & INTEGRATION
# ==============================================================================
with tab_api:
    st.markdown("### 🔌 REST API Endpoints & Production Integration")
    st.markdown("Both models are wrapped in a production FastAPI service for microservice orchestration.")
    
    st.code("""
# Start the FastAPI Service:
# uvicorn api:app --host 0.0.0.0 --port 8000

# 1. PM2.5 Forecast Request (Autonomous VAR)
curl -X POST "http://localhost:8000/forecast/pm25" \\
     -H "Content-Type: application/json" \\
     -d '{"horizon_days": 7, "scenario": "autonomous_var", "confidence_level": 0.95}'

# 2. PM2.5 Forecast Request (Winter Inversion Surge)
curl -X POST "http://localhost:8000/forecast/pm25" \\
     -H "Content-Type: application/json" \\
     -d '{"horizon_days": 7, "scenario": "winter_inversion", "confidence_level": 0.95}'

# 3. NIFTY 50 GARCH Volatility Forecast
curl -X POST "http://localhost:8000/forecast/volatility" \\
     -H "Content-Type: application/json" \\
     -d '{"horizon_days": 5, "confidence_level": 0.95}'
    """, language="bash")
    
    st.markdown("#### Sample JSON Output Payload (`/forecast/pm25`)")
    sample_json = pipeline.forecast_pm25(horizon_days=3, scenario="autonomous_var")
    st.json(sample_json)
