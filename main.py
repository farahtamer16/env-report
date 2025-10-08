import os, yaml
from pathlib import Path
from data_fetch import fetch_openaq
from indicators import daily_agg, compute_kpis
from plotting import plot_timeseries, plot_rolling
from report_builder import render_markdown

def main(cfg_path="config.example.yaml"):
    with open(cfg_path, "r") as f:
        cfg = yaml.safe_load(f)

    city     = cfg["region"]["city"]
    country  = cfg["region"].get("country")
    start    = cfg["period"]["start"]
    end      = cfg["period"]["end"]
    param    = cfg["air"]["parameter"]
    who_thr  = float(cfg["air"]["who_24h_guideline"])
    name     = cfg["output"]["report_name"]

    out_charts = Path("outputs/charts"); out_charts.mkdir(parents=True, exist_ok=True)
    out_reports = Path("outputs/reports"); out_reports.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] Fetching OpenAQ data for {city} ({country or '—'}) {param} {start}→{end} …")
    df = fetch_openaq(city=city, country=country, parameter=param, date_from=start, date_to=end)
    if df.empty:
        print("No data returned. Try another city/date range/parameter.")
        return

    print(f"[2/4] Aggregating daily means …")
    daily = daily_agg(df)
    daily_path = out_reports / f"{name}_daily.csv"
    daily.to_csv(daily_path, index=False)

    print(f"[3/4] Computing KPIs …")
    kpis = compute_kpis(daily, who_thr)
    print(kpis)

    print(f"[4/4] Plotting charts …")
    ts_path = out_charts / f"{name}_timeseries.png"
    plot_timeseries(daily, who_thr, f"{city} — {param.upper()} Daily Mean", str(ts_path))
    roll_path = out_charts / f"{name}_rolling30.png"
    plot_rolling(daily, 30, f"{city} — {param.upper()} 30-day Rolling Mean", str(roll_path))

    print("Building Markdown report …")
    md = render_markdown(city, param, start, end, kpis, who_thr, name, window=30)
    md_path = out_reports / f"{name}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)

    print(f"\nDone ✅\n- Charts: {ts_path.name}, {roll_path.name}\n- Daily CSV: {daily_path.name}\n- Report (Markdown): {md_path.name}\n")

if __name__ == "__main__":
    main()
