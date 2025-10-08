# plotting.py
import os
import matplotlib.pyplot as plt
import pandas as pd

# ---------- file-saving plots (used by CLI) ----------
def plot_timeseries(daily_df: pd.DataFrame, who_guideline: float, title: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    fig = plt.figure()
    plt.plot(daily_df["date"], daily_df["mean"], label="Daily mean")
    plt.axhline(y=who_guideline, linestyle="--", label=f"WHO 24h guideline ({who_guideline})")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("µg/m³")
    plt.legend()
    plt.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)

def plot_rolling(daily_df: pd.DataFrame, window: int, title: str, out_path: str):
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    dd = daily_df.copy()
    dd["roll"] = dd["mean"].rolling(window=window, min_periods=max(7, window//4)).mean()
    fig = plt.figure()
    plt.plot(dd["date"], dd["roll"], label=f"{window}-day rolling mean")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("µg/m³")
    plt.legend()
    plt.tight_layout()
    fig.savefig(out_path, dpi=140)
    plt.close(fig)

# ---------- figure-returning plots (used by Streamlit) ----------
def fig_timeseries(daily_df: pd.DataFrame, who_guideline: float, title: str):
    fig = plt.figure()
    plt.plot(daily_df["date"], daily_df["mean"], label="Daily mean")
    plt.axhline(y=who_guideline, linestyle="--", label=f"WHO 24h guideline ({who_guideline})")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("µg/m³")
    plt.legend()
    plt.tight_layout()
    return fig

def fig_rolling(daily_df: pd.DataFrame, window: int, title: str):
    dd = daily_df.copy()
    dd["roll"] = dd["mean"].rolling(window=window, min_periods=max(7, window//4)).mean()
    fig = plt.figure()
    plt.plot(dd["date"], dd["roll"], label=f"{window}-day rolling mean")
    plt.title(title)
    plt.xlabel("Date")
    plt.ylabel("µg/m³")
    plt.legend()
    plt.tight_layout()
    return fig
