# pipeline.py
from data_fetch import fetch_city_parameter_daily
from indicators import daily_agg, compute_kpis
from report_builder import render_markdown
from plotting import fig_timeseries, fig_rolling

def run_analysis(city: str, country, param: str,
                 start: str, end: str, who_thr: float,
                 report_name: str, rolling_window: int = 30):
    df, fetch_err = fetch_city_parameter_daily(country, city, param, start, end)
    if fetch_err:
        return {"error": fetch_err}
    if df.empty:
        return {"error": "No data returned. Try another city/parameter/date range."}

    # We combined several sensors; aggregate to daily mean across sensors
    daily = df.set_index("datetime")["value"].resample("D").mean().reset_index()
    daily["date"] = daily["datetime"].dt.tz_convert(None).dt.date
    daily = daily.rename(columns={"value": "mean"})[["date","mean"]]
    # fabricate median/count for compatibility with the KPI/plot code
    daily["median"] = daily["mean"]
    daily["n"] = 1

    kpis = compute_kpis(daily, who_thr)

    ts_fig = fig_timeseries(daily, who_thr, f"{city} — {param.upper()} Daily Mean")
    roll_fig = fig_rolling(daily, rolling_window, f"{city} — {param.upper()} {rolling_window}-day Rolling Mean")

    md = render_markdown(city, param, start, end, kpis, who_thr, report_name,
                        window=rolling_window, include_images=False)  # <-- app mode

    return {
        "daily": daily,
        "kpis": kpis,
        "ts_fig": ts_fig,
        "roll_fig": roll_fig,
        "report_md": md
    }
