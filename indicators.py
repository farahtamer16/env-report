import pandas as pd
import numpy as np

def daily_agg(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["date","mean","median","n"])
    s = df.set_index("datetime")["value"]
    daily = s.resample("D").agg(["mean","median","count"])
    daily.index = daily.index.tz_convert(None).date
    out = daily.reset_index()
    out.columns = ["date","mean","median","n"]
    return out

def compute_kpis(daily_df: pd.DataFrame, who_24h_guideline: float) -> dict:
    if daily_df.empty:
        return {
            "days_total": 0, "days_exceed": 0, "exceed_pct": 0.0,
            "mean": None, "median": None, "p95": None, "trend_pct_90d": None
        }
    dd = daily_df.dropna(subset=["mean"]).copy()
    dd["date"] = pd.to_datetime(dd["date"])
    days_total = dd.shape[0]
    days_exceed = int((dd["mean"] > who_24h_guideline).sum())
    exceed_pct = round((days_exceed / days_total * 100.0), 2) if days_total else 0.0

    dd = dd.sort_values("date")
    dd["roll90"] = dd["mean"].rolling(window=90, min_periods=30).mean()
    last90 = dd["roll90"].iloc[-1] if dd["roll90"].notna().iloc[-1] else None
    prev90 = dd["roll90"].iloc[-91] if dd.shape[0] > 180 else None
    trend_pct_90d = None
    if (last90 is not None) and (prev90 is not None) and prev90:
        trend_pct_90d = round((last90 / prev90 - 1.0) * 100.0, 2)

    return {
        "days_total": days_total,
        "days_exceed": days_exceed,
        "exceed_pct": exceed_pct,
        "mean": round(dd["mean"].mean(), 2),
        "median": round(dd["median"].median(), 2),
        "p95": round(dd["mean"].quantile(0.95), 2),
        "trend_pct_90d": trend_pct_90d
    }
