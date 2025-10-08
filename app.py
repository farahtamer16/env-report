import streamlit as st
from datetime import date, timedelta
from pipeline import run_analysis
from data_fetch import list_cities, list_sensors_in_city

@st.cache_data(ttl=3600)
def _cities_cached(iso, param):
    return list_cities(iso, param)

@st.cache_data(ttl=3600)
def _sensors_cached(iso, city, param):
    return list_sensors_in_city(iso, city, param)

st.set_page_config(page_title="AI Environmental Report", page_icon="🌍", layout="wide")
st.title("🌍 AI Environmental Report Generator (OpenAQ)")
st.caption("Live analytics + auto-written brief. Pick a country, city, pollutant, and dates.")

with st.sidebar:
    st.header("Controls")

    country = st.text_input("Country ISO (e.g., IN, US, SA)", value="IN").upper()
    param = st.selectbox("Pollutant", ["pm25","pm10","no2","o3","so2","co"], index=0)

    # City picker
    city_opts, c_err = _cities_cached(country, param)
    if c_err:
        st.warning(c_err)
        city = st.text_input("City (free text)", value="New Delhi")
    else:
        city = st.selectbox("City", city_opts, index=0)

    # Optional: sensor picker (let user aggregate or pick specific sensors)
    show_sensors = st.checkbox("Pick specific sensors (optional)")
    selected_sensor_ids = []
    if show_sensors and city:
        sensors, s_err = _sensors_cached(country, city, param)
        if s_err:
            st.warning(s_err)
        else:
            selected_sensor_ids = st.multiselect(
                "Sensors", options=[sid for sid,_ in sensors],
                format_func=lambda sid: next(lbl for sid2,lbl in sensors if sid2==sid)
            )

    today = date.today()
    default_start = today - timedelta(days=365)
    start = st.date_input("Start date", value=default_start)
    end = st.date_input("End date", value=today)
    who = st.number_input("WHO 24h guideline (µg/m³)", value=15.0, step=1.0, format="%.1f")
    report_name = st.text_input("Report name", value=f"{city}_{param}_{start}_{end}".replace(" ","_"))

    run_btn = st.button("Generate")

def _dstr(d): return d.strftime("%Y-%m-%d")

if run_btn:
    with st.spinner("Fetching & analyzing…"):
        res = run_analysis(
            city=city.strip(),
            country=(country.strip() or None),
            param=param,
            start=_dstr(start),
            end=_dstr(end),
            who_thr=float(who),
            report_name=report_name
        )

    if not res or "error" in res:
        st.warning(res.get("error", "No data returned. Try another city/parameter/date range."))
    else:
        k = res["kpis"]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Days", k["days_total"])
        c2.metric("Exceedance Days", k["days_exceed"], f'{k["exceed_pct"]}%')
        c3.metric("Mean (µg/m³)", k["mean"])
        c4.metric("90d Trend", f'{k["trend_pct_90d"]}%' if k["trend_pct_90d"] is not None else "N/A")

        st.subheader("Charts")
        colA, colB = st.columns(2)
        with colA: st.pyplot(res["ts_fig"], use_container_width=True)
        with colB: st.pyplot(res["roll_fig"], use_container_width=True)

        with st.expander("Daily data (download)"):
            st.dataframe(res["daily"], use_container_width=True)
            csv = res["daily"].to_csv(index=False).encode("utf-8")
            st.download_button("Download CSV", csv, file_name=f"{report_name}_daily.csv", mime="text/csv")

        st.subheader("AI-Generated Brief")
        st.markdown(res["report_md"])

        md_bytes = res["report_md"].encode("utf-8")
        st.download_button("Download Markdown Report", md_bytes, file_name=f"{report_name}.md", mime="text/markdown")
else:
    st.info("Set your inputs in the sidebar and click **Generate**.")
