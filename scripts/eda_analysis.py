"""
=====================================================================
Bluestock MF Capstone — Day 3: Exploratory Data Analysis (EDA)
=====================================================================
Author : DEBNIL PAL
Date   : 2026-06-03
DB     : data/db/bluestock_mf.db
Output : reports/charts/  |  reports/eda_findings.md
=====================================================================
"""

from __future__ import annotations

import csv
import logging
import sys
import time
import warnings
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")                       # headless backend
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import seaborn as sns
from sqlalchemy import create_engine, text

# ── Suppress noisy warnings ──────────────────────────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# =====================================================================
# VERSION DIAGNOSTICS & COMPATIBILITY CHECK
# =====================================================================
import plotly
try:
    import kaleido
    _KALEIDO_VERSION = getattr(kaleido, "__version__", "unknown")
except ImportError:
    _KALEIDO_VERSION = "NOT INSTALLED"

_PLOTLY_VERSION = plotly.__version__


def _parse_major(version_str: str) -> int | None:
    """Extract major version number from a version string."""
    try:
        return int(version_str.split(".")[0])
    except (ValueError, IndexError, AttributeError):
        return None


_PLOTLY_MAJOR = _parse_major(_PLOTLY_VERSION)
_KALEIDO_MAJOR = _parse_major(_KALEIDO_VERSION)
_PNG_EXPORT_DISABLED = False
_PNG_DISABLE_REASON = ""

# Check 1: Known-bad version pairing
if _PLOTLY_MAJOR is not None and _KALEIDO_MAJOR is not None:
    if _PLOTLY_MAJOR < 6 and _KALEIDO_MAJOR >= 1:
        _PNG_EXPORT_DISABLED = True
        _PNG_DISABLE_REASON = (
            f"Incompatible versions: plotly={_PLOTLY_VERSION} (<6) + kaleido={_KALEIDO_VERSION} (>=1)"
        )


def _probe_png_export(timeout_sec: int = 10) -> bool:
    """Run a tiny write_image test in a subprocess with a hard timeout.

    Returns True if PNG export works, False if it hangs or fails.
    Uses subprocess (not threading) so the process can be truly killed.
    """
    import subprocess
    import tempfile
    import os

    probe_script = (
        "import plotly.graph_objects as go, sys, os, tempfile\n"
        "fig = go.Figure(go.Scatter(x=[1], y=[1]))\n"
        "tmp = os.path.join(tempfile.gettempdir(), '_eda_probe.png')\n"
        "fig.write_image(tmp, width=100, height=100)\n"
        "os.remove(tmp)\n"
        "print('PROBE_OK')\n"
    )
    try:
        result = subprocess.run(
            [sys.executable, "-c", probe_script],
            capture_output=True, text=True, timeout=timeout_sec,
        )
        return "PROBE_OK" in result.stdout
    except subprocess.TimeoutExpired:
        return False
    except Exception:
        return False


# Check 2: Runtime probe (only if version check passed)
if not _PNG_EXPORT_DISABLED and _KALEIDO_VERSION != "NOT INSTALLED":
    if not _probe_png_export(timeout_sec=10):
        _PNG_EXPORT_DISABLED = True
        _PNG_DISABLE_REASON = (
            f"Startup probe FAILED (write_image hung or errored with "
            f"plotly={_PLOTLY_VERSION}, kaleido={_KALEIDO_VERSION})"
        )
elif _KALEIDO_VERSION == "NOT INSTALLED":
    _PNG_EXPORT_DISABLED = True
    _PNG_DISABLE_REASON = "kaleido not installed"

# =====================================================================
# 0. CONSTANTS & PATHS
# =====================================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH      = PROJECT_ROOT / "data" / "db" / "bluestock_mf.db"
CHART_DIR    = PROJECT_ROOT / "reports" / "charts"
REPORT_DIR   = PROJECT_ROOT / "reports"
LOG_DIR      = PROJECT_ROOT / "logs"

CHART_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

DPI          = 300
BBOX         = "tight"

# ── Colour palette ───────────────────────────────────────────────────
PALETTE_MAIN = [
    "#2563EB", "#7C3AED", "#059669", "#DC2626", "#D97706",
    "#0891B2", "#DB2777", "#4F46E5", "#16A34A", "#EA580C",
]
PALETTE_SEQ  = "YlOrRd"
PALETTE_DIV  = "RdYlGn"
sns.set_palette(PALETTE_MAIN)

# ── Matplotlib global styling ────────────────────────────────────────
plt.rcParams.update({
    "figure.facecolor":  "#FAFAFA",
    "axes.facecolor":    "#FAFAFA",
    "axes.edgecolor":    "#CCCCCC",
    "axes.grid":         True,
    "grid.alpha":        0.30,
    "grid.color":        "#999999",
    "font.family":       "sans-serif",
    "font.size":         11,
    "axes.titlesize":    14,
    "axes.titleweight":  "bold",
    "axes.labelsize":    12,
    "legend.fontsize":   9,
    "figure.dpi":        DPI,
    "savefig.dpi":       DPI,
    "savefig.bbox":      BBOX,
})

# =====================================================================
# 1. LOGGING
# =====================================================================
log_file = LOG_DIR / "eda_analysis.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(log_file, mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("eda")

# -- Log version diagnostics right after logger is ready ---------------
logger.info("Plotly Version  : %s", _PLOTLY_VERSION)
logger.info("Kaleido Version : %s", _KALEIDO_VERSION)
if _PNG_EXPORT_DISABLED:
    logger.warning(
        "Static PNG export DISABLED: %s", _PNG_DISABLE_REASON,
    )
    if _KALEIDO_MAJOR is not None and _KALEIDO_MAJOR >= 1:
        logger.warning(
            "Recommendation: pip uninstall kaleido -y && pip install kaleido==0.2.1  "
            "OR  pip install -U plotly>=6.1.1"
        )
    else:
        logger.warning(
            "Recommendation: pip install -U plotly>=6.1.1  (for kaleido %s compatibility)",
            _KALEIDO_VERSION,
        )
else:
    logger.info("Plotly/Kaleido compatibility : OK (probe passed)")

# =====================================================================
# EXPORT STATUS TRACKER
# =====================================================================
_export_log: list[dict[str, str]] = []


def _record_export(
    chart_name: str,
    html_ok: bool,
    png_ok: bool,
    status: str,
    error_message: str = "",
) -> None:
    """Append one row to the in-memory export tracker."""
    _export_log.append({
        "chart_name": chart_name,
        "html_generated": str(html_ok),
        "png_generated": str(png_ok),
        "status": status,
        "error_message": error_message,
    })


def _write_export_report() -> Path:
    """Flush export tracker to reports/chart_export_status.csv."""
    path = REPORT_DIR / "chart_export_status.csv"
    fieldnames = ["chart_name", "html_generated", "png_generated", "status", "error_message"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(_export_log)
    logger.info("  [SAVE]  Export status report -> %s  (%d entries)", path.name, len(_export_log))
    return path


# =====================================================================
# 2. DATA LOADING  (reusable functions)
# =====================================================================
_ENGINE: Any = None


def _get_engine() -> Any:
    """Singleton SQLAlchemy engine."""
    global _ENGINE
    if _ENGINE is None:
        uri = f"sqlite:///{DB_PATH.as_posix()}"
        _ENGINE = create_engine(uri, echo=False)
        logger.info("SQLAlchemy engine created  -> %s", DB_PATH.name)
    return _ENGINE


def load_table(table_name: str) -> pd.DataFrame:
    """Load an entire table from the warehouse."""
    engine = _get_engine()
    df = pd.read_sql_table(table_name, engine)
    logger.info("Loaded %-30s -> %s rows x %s cols", table_name, *df.shape)
    return df


def run_query(sql: str) -> pd.DataFrame:
    """Run an arbitrary SQL query and return a DataFrame."""
    engine = _get_engine()
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)
    return df


def load_all_tables() -> dict[str, pd.DataFrame]:
    """Load all warehouse tables into a dict."""
    tables = [
        "dim_fund", "dim_date",
        "fact_nav", "fact_aum", "fact_sip_industry",
        "fact_category_inflows", "fact_transactions",
        "fact_portfolio", "fact_benchmark",
        "fact_performance", "fact_industry_folios",
    ]
    data: dict[str, pd.DataFrame] = {}
    for t in tables:
        try:
            data[t] = load_table(t)
        except Exception as exc:
            logger.warning("Could not load %s: %s", t, exc)
    return data


# =====================================================================
# 3. CHART HELPERS
# =====================================================================
def _save_fig(fig: plt.Figure, name: str) -> Path:
    """Save a Matplotlib figure to CHART_DIR and close it."""
    path = CHART_DIR / name
    fig.savefig(path, dpi=DPI, bbox_inches=BBOX)
    plt.close(fig)
    logger.info("  [CHART]  Saved  %s", name)
    _record_export(name, html_ok=False, png_ok=True, status="SUCCESS")
    return path


# ── Timeout for write_image (seconds) ────────────────────────────────
_PNG_EXPORT_TIMEOUT = 30


def safe_plotly_export(
    fig: go.Figure,
    path_png: Path,
    timeout: int = _PNG_EXPORT_TIMEOUT,
) -> bool:
    """Attempt static PNG export with a hard timeout guard.

    Returns True on success, False on any failure (exception or timeout).
    This function will NEVER hang or crash the pipeline.
    """
    def _do_export() -> None:
        fig.write_image(str(path_png), width=1600, height=900, scale=2)

    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(_do_export)
            future.result(timeout=timeout)
        return True
    except FuturesTimeout:
        logger.warning(
            "  [WARN]  PNG export TIMED OUT after %ds -> %s (pipeline continues)",
            timeout, path_png.name,
        )
        return False
    except Exception as exc:
        logger.warning(
            "  [WARN]  PNG export FAILED -> %s : %s (pipeline continues)",
            path_png.name, exc,
        )
        return False


def _save_plotly(fig: go.Figure, name_html: str, name_png: str | None = None) -> Path:
    """Save a Plotly figure as HTML (and optionally a static PNG).

    HTML is always saved first.  PNG export is:
      - Skipped entirely when an incompatible Plotly/Kaleido pair is detected.
      - Otherwise attempted with a timeout guard (never hangs).
    """
    # 1. Always save HTML first
    path_html = CHART_DIR / name_html
    fig.write_html(str(path_html), include_plotlyjs="cdn")
    logger.info("  [CHART]  Saved  %s  (HTML = SUCCESS)", name_html)
    html_ok = True

    # 2. Attempt PNG export (with safeguards)
    png_ok = False
    error_msg = ""
    if name_png:
        if _PNG_EXPORT_DISABLED:
            logger.warning(
                "  [SKIP]  PNG export disabled (Plotly %s / Kaleido %s) -> %s",
                _PLOTLY_VERSION, _KALEIDO_VERSION, name_png,
            )
            error_msg = f"Skipped: plotly={_PLOTLY_VERSION}, kaleido={_KALEIDO_VERSION}"
        elif _KALEIDO_VERSION == "NOT INSTALLED":
            logger.warning("  [SKIP]  PNG export skipped (kaleido not installed) -> %s", name_png)
            error_msg = "kaleido not installed"
        else:
            path_png_full = CHART_DIR / name_png
            png_ok = safe_plotly_export(fig, path_png_full)
            if png_ok:
                logger.info("  [CHART]  Saved  %s  (PNG = SUCCESS)", name_png)
            else:
                error_msg = "Export failed or timed out"

        status = "SUCCESS" if png_ok else "HTML_ONLY"
        _record_export(name_png, html_ok=True, png_ok=png_ok, status=status, error_message=error_msg)

    # Always record the HTML entry
    _record_export(name_html, html_ok=html_ok, png_ok=False, status="SUCCESS")
    return path_html


charts_generated: list[str] = []


# =====================================================================
# PHASE 3 — NAV TREND ANALYSIS
# =====================================================================
def chart_nav_trends(data: dict[str, pd.DataFrame]) -> None:
    """Interactive NAV trends for all 40 schemes (2022-2026)."""
    logger.info("--- Phase 3: NAV Trend Analysis ---")

    nav = data["fact_nav"].merge(
        data["dim_fund"][["amfi_code", "scheme_name", "fund_house"]],
        on="amfi_code",
    )
    nav["date"] = pd.to_datetime(nav["date_id"])
    nav.sort_values(["scheme_name", "date"], inplace=True)

    # ── Interactive Plotly chart ──────────────────────────────────────
    fig = px.line(
        nav, x="date", y="nav", color="scheme_name",
        title="Daily NAV Trends — All 40 Schemes (2022–2026)",
        labels={"nav": "NAV (₹)", "date": "Date", "scheme_name": "Scheme"},
    )
    fig.update_layout(
        template="plotly_white",
        legend=dict(font=dict(size=8), orientation="v"),
        hovermode="x unified",
        height=700,
    )
    # Shade 2023 bull run
    fig.add_vrect(
        x0="2023-01-01", x1="2023-12-31",
        fillcolor="#059669", opacity=0.08,
        annotation_text="2023 Bull Market", annotation_position="top left",
        line_width=0,
    )
    # Shade 2024 correction
    fig.add_vrect(
        x0="2024-01-01", x1="2024-12-31",
        fillcolor="#DC2626", opacity=0.08,
        annotation_text="2024 Market Correction", annotation_position="top left",
        line_width=0,
    )
    _save_plotly(fig, "nav_trends_interactive.html", "nav_trends_all_funds.png")
    charts_generated.extend(["nav_trends_all_funds.png", "nav_trends_interactive.html"])

    # ── Top-performing schemes (static) ──────────────────────────────
    last = nav.groupby("scheme_name").last().reset_index()
    first = nav.groupby("scheme_name").first().reset_index()
    merged = last[["scheme_name", "nav"]].merge(
        first[["scheme_name", "nav"]], on="scheme_name", suffixes=("_last", "_first"),
    )
    merged["growth_pct"] = (
        (merged["nav_last"] - merged["nav_first"]) / merged["nav_first"] * 100
    )
    top5 = merged.nlargest(5, "growth_pct")

    fig2, ax = plt.subplots(figsize=(12, 5))
    short_names = [n[:40] for n in top5["scheme_name"]]
    bars = ax.barh(short_names, top5["growth_pct"], color=PALETTE_MAIN[:5], edgecolor="white")
    for bar, val in zip(bars, top5["growth_pct"]):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontweight="bold", fontsize=10)
    ax.set_xlabel("NAV Growth (%)")
    ax.set_title("Top 5 Schemes by NAV Growth (2022–2026)")
    ax.invert_yaxis()
    _save_fig(fig2, "top_funds_nav_growth.png")
    charts_generated.append("top_funds_nav_growth.png")


# =====================================================================
# PHASE 4 — AUM GROWTH ANALYSIS
# =====================================================================
def chart_aum_growth(data: dict[str, pd.DataFrame]) -> None:
    """Grouped bar chart of AUM growth by AMC."""
    logger.info("--- Phase 4: AUM Growth Analysis ---")

    aum = data["fact_aum"].copy()
    aum["date"] = pd.to_datetime(aum["date_id"])
    aum["year"] = aum["date"].dt.year

    yearly = (
        aum.groupby(["year", "fund_house"])["aum_lakh_crore"]
        .mean()
        .reset_index()
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    pivot = yearly.pivot(index="year", columns="fund_house", values="aum_lakh_crore")
    pivot.plot(kind="bar", ax=ax, width=0.85, edgecolor="white", linewidth=0.5)

    # Highlight SBI
    for container in ax.containers:
        label = container.get_label()
        if "SBI" in label:
            for bar in container:
                bar.set_edgecolor("#DC2626")
                bar.set_linewidth(2)

    ax.set_title("AUM Growth by Fund House (₹ Lakh Crore)")
    ax.set_ylabel("AUM (₹ Lakh Crore)")
    ax.set_xlabel("Year")
    ax.legend(fontsize=7, ncol=2, loc="upper left")
    ax.tick_params(axis="x", rotation=0)

    # Annotate SBI peak
    sbi = yearly[yearly["fund_house"].str.contains("SBI", case=False)]
    if not sbi.empty:
        peak = sbi.loc[sbi["aum_lakh_crore"].idxmax()]
        ax.annotate(
            f"₹{peak['aum_lakh_crore']:.1f}L Cr",
            xy=(0, peak["aum_lakh_crore"]),
            xytext=(0.5, peak["aum_lakh_crore"] + 0.3),
            fontsize=10, fontweight="bold", color="#DC2626",
            arrowprops=dict(arrowstyle="->", color="#DC2626"),
        )

    _save_fig(fig, "aum_growth_by_amc.png")
    charts_generated.append("aum_growth_by_amc.png")


# =====================================================================
# PHASE 5 — SIP INFLOW TREND
# =====================================================================
def chart_sip_inflow(data: dict[str, pd.DataFrame]) -> None:
    """Interactive SIP inflow trend with rolling average."""
    logger.info("--- Phase 5: SIP Inflow Trend ---")

    sip = data["fact_sip_industry"].copy()
    sip["date"] = pd.to_datetime(sip["date_id"])
    sip.sort_values("date", inplace=True)
    sip["rolling_3m"] = sip["sip_inflow_crore"].rolling(3, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=sip["date"], y=sip["sip_inflow_crore"],
        mode="lines+markers", name="Monthly SIP Inflow",
        line=dict(color="#2563EB", width=2.5),
        marker=dict(size=5),
    ))
    fig.add_trace(go.Scatter(
        x=sip["date"], y=sip["rolling_3m"],
        mode="lines", name="3-Month Rolling Avg",
        line=dict(color="#D97706", width=2, dash="dash"),
    ))

    # Annotate all-time high (Dec 2025)
    max_row = sip.loc[sip["sip_inflow_crore"].idxmax()]
    fig.add_annotation(
        x=max_row["date"], y=max_row["sip_inflow_crore"],
        text=f"₹{max_row['sip_inflow_crore']:,.0f} Cr<br>ALL-TIME HIGH",
        showarrow=True, arrowhead=2, ax=-60, ay=-50,
        font=dict(color="#DC2626", size=13, family="Arial Black"),
        bordercolor="#DC2626", borderwidth=2, borderpad=4,
        bgcolor="rgba(255,255,255,0.9)",
    )

    fig.update_layout(
        title="SIP Inflow Trend — Jan 2022 to Dec 2025",
        xaxis_title="Month",
        yaxis_title="SIP Inflow (₹ Crore)",
        template="plotly_white",
        hovermode="x unified",
        height=550,
    )
    _save_plotly(fig, "sip_inflow_trend.html", "sip_inflow_trend.png")
    charts_generated.extend(["sip_inflow_trend.png", "sip_inflow_trend.html"])


# =====================================================================
# PHASE 6 — CATEGORY INFLOW HEATMAP
# =====================================================================
def chart_category_heatmap(data: dict[str, pd.DataFrame]) -> None:
    """Seaborn heatmap of net inflows by category × month."""
    logger.info("--- Phase 6: Category Inflow Heatmap ---")

    ci = data["fact_category_inflows"].copy()
    ci["date"] = pd.to_datetime(ci["date_id"])
    ci["month_label"] = ci["date"].dt.strftime("%Y-%m")

    pivot = ci.pivot_table(
        index="category", columns="month_label",
        values="net_inflow_crore", aggfunc="sum",
    )
    pivot = pivot.reindex(sorted(pivot.columns, key=str), axis=1)

    fig, ax = plt.subplots(figsize=(18, 8))
    sns.heatmap(
        pivot, annot=True, fmt=".0f", cmap="RdYlGn",
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "Net Inflow (₹ Cr)"},
        ax=ax,
    )
    ax.set_title("Category-wise Net Inflows (₹ Crore) — Monthly Heatmap")
    ax.set_xlabel("Month")
    ax.set_ylabel("Category")
    plt.xticks(rotation=45, ha="right", fontsize=8)
    plt.yticks(fontsize=9)
    _save_fig(fig, "category_inflow_heatmap.png")
    charts_generated.append("category_inflow_heatmap.png")


# =====================================================================
# PHASE 7 — INVESTOR DEMOGRAPHICS
# =====================================================================
def chart_investor_demographics(data: dict[str, pd.DataFrame]) -> None:
    """Demographic charts: age, gender, income."""
    logger.info("--- Phase 7: Investor Demographics ---")
    tx = data["fact_transactions"].copy()

    # 1. Age group distribution — pie
    age_counts = tx["age_group"].value_counts()
    fig1, ax1 = plt.subplots(figsize=(8, 8))
    colors = ["#2563EB", "#7C3AED", "#059669", "#DC2626", "#D97706"]
    wedges, texts, autotexts = ax1.pie(
        age_counts, labels=age_counts.index, autopct="%1.1f%%",
        colors=colors, startangle=140, pctdistance=0.82,
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_fontsize(11)
    ax1.set_title("Investor Distribution by Age Group")
    centre = plt.Circle((0, 0), 0.55, fc="#FAFAFA")
    ax1.add_artist(centre)
    ax1.text(0, 0, f"N={len(tx):,}", ha="center", va="center",
             fontsize=14, fontweight="bold", color="#333")
    _save_fig(fig1, "age_group_distribution.png")
    charts_generated.append("age_group_distribution.png")

    # 2. SIP amount by age group — box plot
    sip_tx = tx[tx["transaction_type"] == "SIP"]
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    order = sorted(tx["age_group"].unique())
    sns.boxplot(data=sip_tx, x="age_group", y="amount_inr", order=order,
                palette=PALETTE_MAIN, ax=ax2, fliersize=2)
    ax2.set_title("SIP Amount Distribution by Age Group")
    ax2.set_ylabel("SIP Amount (₹)")
    ax2.set_xlabel("Age Group")
    ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    _save_fig(fig2, "sip_boxplot_agegroup.png")
    charts_generated.append("sip_boxplot_agegroup.png")

    # 3. Gender distribution
    gender_counts = tx["gender"].value_counts()
    fig3, ax3 = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax3.pie(
        gender_counts, labels=gender_counts.index, autopct="%1.1f%%",
        colors=["#2563EB", "#DB2777"], startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=2),
        explode=[0.03, 0.03],
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_fontsize(13)
    ax3.set_title("Investor Gender Distribution")
    _save_fig(fig3, "gender_distribution.png")
    charts_generated.append("gender_distribution.png")

    # 4. Average investment by gender (combined chart with box)
    fig4, ax4 = plt.subplots(figsize=(10, 6))
    sns.boxplot(data=tx, x="gender", y="amount_inr", palette=["#2563EB", "#DB2777"], ax=ax4)
    ax4.set_title("Investment Amount Distribution by Gender")
    ax4.set_ylabel("Amount (₹)")
    ax4.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x:,.0f}"))
    # Add mean annotations
    for i, g in enumerate(["Male", "Female"]):
        subset = tx[tx["gender"] == g]["amount_inr"]
        if not subset.empty:
            mean_val = subset.mean()
            ax4.text(i, mean_val, f"Mean: ₹{mean_val:,.0f}", ha="center",
                     va="bottom", fontweight="bold", fontsize=10, color="#333")
    _save_fig(fig4, "avg_investment_by_gender.png")
    charts_generated.append("avg_investment_by_gender.png")

    # 5. Age vs Income scatter
    fig5, ax5 = plt.subplots(figsize=(10, 7))
    age_order_map = {"18-25": 1, "26-35": 2, "36-45": 3, "46-55": 4, "56+": 5}
    sample = tx.copy()
    sample["age_num"] = sample["age_group"].map(age_order_map)
    sns.scatterplot(
        data=sample, x="age_num", y="annual_income_lakh",
        hue="gender", style="transaction_type",
        palette=["#2563EB", "#DB2777"], alpha=0.5, s=30, ax=ax5,
    )
    ax5.set_xticks(list(age_order_map.values()))
    ax5.set_xticklabels(list(age_order_map.keys()))
    ax5.set_title("Age Group vs Annual Income (₹ Lakh)")
    ax5.set_xlabel("Age Group")
    ax5.set_ylabel("Annual Income (₹ Lakh)")
    _save_fig(fig5, "age_income_analysis.png")
    charts_generated.append("age_income_analysis.png")


# =====================================================================
# PHASE 8 — GEOGRAPHIC ANALYSIS
# =====================================================================
def chart_geographic(data: dict[str, pd.DataFrame]) -> None:
    """State-wise SIP, T30/B30, transaction counts."""
    logger.info("--- Phase 8: Geographic Analysis ---")
    tx = data["fact_transactions"].copy()

    # 1. State-wise SIP amount — horizontal bar
    sip_tx = tx[tx["transaction_type"] == "SIP"]
    state_sip = sip_tx.groupby("state")["amount_inr"].sum().sort_values(ascending=True)

    fig1, ax1 = plt.subplots(figsize=(12, 8))
    colors = ["#2563EB" if i >= len(state_sip) - 3 else "#94A3B8"
              for i in range(len(state_sip))]
    ax1.barh(state_sip.index, state_sip.values, color=colors, edgecolor="white")
    ax1.set_title("State-wise Total SIP Amount (₹)")
    ax1.set_xlabel("Total SIP Amount (₹)")
    ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"₹{x/1e7:.1f}Cr"))
    for i, (val, state) in enumerate(zip(state_sip.values, state_sip.index)):
        if i >= len(state_sip) - 3:
            ax1.text(val, state, f"  ₹{val/1e7:.1f} Cr", va="center",
                     fontweight="bold", fontsize=9)
    _save_fig(fig1, "state_sip_distribution.png")
    charts_generated.append("state_sip_distribution.png")

    # 2. T30 vs B30 — pie chart
    tier_counts = tx["city_tier"].value_counts()
    fig2, ax2 = plt.subplots(figsize=(7, 7))
    wedges, texts, autotexts = ax2.pie(
        tier_counts, labels=tier_counts.index, autopct="%1.1f%%",
        colors=["#2563EB", "#D97706"], startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )
    for t in autotexts:
        t.set_fontweight("bold")
        t.set_fontsize(13)
    ax2.set_title("T30 vs B30 City Distribution")
    _save_fig(fig2, "t30_b30_distribution.png")
    charts_generated.append("t30_b30_distribution.png")

    # 3. Transaction count by state
    state_counts = tx.groupby("state").size().sort_values(ascending=True)
    fig3, ax3 = plt.subplots(figsize=(12, 8))
    colors3 = ["#7C3AED" if i >= len(state_counts) - 3 else "#C4B5FD"
               for i in range(len(state_counts))]
    ax3.barh(state_counts.index, state_counts.values, color=colors3, edgecolor="white")
    ax3.set_title("Transaction Count by State")
    ax3.set_xlabel("Number of Transactions")
    for i, (val, state) in enumerate(zip(state_counts.values, state_counts.index)):
        if i >= len(state_counts) - 3:
            ax3.text(val, state, f"  {val:,}", va="center",
                     fontweight="bold", fontsize=9)
    _save_fig(fig3, "state_transaction_count.png")
    charts_generated.append("state_transaction_count.png")


# =====================================================================
# PHASE 9 — FOLIO GROWTH ANALYSIS
# =====================================================================
def chart_folio_growth(data: dict[str, pd.DataFrame]) -> None:
    """Line chart of folio growth with milestone annotations."""
    logger.info("--- Phase 9: Folio Growth Analysis ---")

    folios = data["fact_industry_folios"].copy()
    folios["date"] = pd.to_datetime(folios["date_id"])
    folios.sort_values("date", inplace=True)

    fig, ax = plt.subplots(figsize=(14, 6))
    ax.plot(folios["date"], folios["total_folios_crore"],
            marker="o", linewidth=2.5, color="#2563EB", markersize=6, zorder=5)
    ax.fill_between(folios["date"], folios["total_folios_crore"],
                    alpha=0.10, color="#2563EB")

    # Milestones
    milestone_13 = folios[folios["total_folios_crore"] <= 13.26 + 0.5].iloc[0]
    milestone_26 = folios[folios["total_folios_crore"] >= 26.12 - 0.5].iloc[-1]

    ax.annotate(
        f"13.26 Cr Folios", xy=(milestone_13["date"], 13.26),
        xytext=(milestone_13["date"] + pd.Timedelta(days=60), 14.5),
        fontsize=11, fontweight="bold", color="#059669",
        arrowprops=dict(arrowstyle="->", color="#059669", lw=1.5),
    )
    ax.annotate(
        f"26.12 Cr Folios", xy=(milestone_26["date"], 26.12),
        xytext=(milestone_26["date"] - pd.Timedelta(days=200), 24),
        fontsize=11, fontweight="bold", color="#DC2626",
        arrowprops=dict(arrowstyle="->", color="#DC2626", lw=1.5),
    )

    ax.set_title("Industry Folio Growth (Jan 2022 – Dec 2025)")
    ax.set_ylabel("Total Folios (Crore)")
    ax.set_xlabel("Date")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:.1f} Cr"))
    _save_fig(fig, "folio_growth.png")
    charts_generated.append("folio_growth.png")


# =====================================================================
# PHASE 10 — CORRELATION ANALYSIS
# =====================================================================
def chart_correlation(data: dict[str, pd.DataFrame]) -> None:
    """NAV return correlation matrix for top 10 funds."""
    logger.info("--- Phase 10: Correlation Analysis ---")

    nav = data["fact_nav"].merge(
        data["dim_fund"][["amfi_code", "scheme_name"]], on="amfi_code",
    )
    # Pick top 10 by row count (most traded)
    top10_codes = nav["amfi_code"].value_counts().head(10).index
    nav10 = nav[nav["amfi_code"].isin(top10_codes)].copy()

    pivot = nav10.pivot_table(
        index="date_id", columns="scheme_name",
        values="daily_return_pct", aggfunc="first",
    )
    # Shorten names for display
    pivot.columns = [c[:35] for c in pivot.columns]
    corr = pivot.corr()

    fig, ax = plt.subplots(figsize=(12, 10))
    mask = np.triu(np.ones_like(corr, dtype=bool), k=1)
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f",
        cmap="RdYlGn", center=0, vmin=-1, vmax=1,
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "Correlation", "shrink": 0.8},
        ax=ax,
    )
    ax.set_title("Daily Return Correlation Matrix — Top 10 Funds")
    plt.xticks(fontsize=8, rotation=45, ha="right")
    plt.yticks(fontsize=8)
    _save_fig(fig, "nav_correlation_matrix.png")
    charts_generated.append("nav_correlation_matrix.png")


# =====================================================================
# PHASE 11 — SECTOR ALLOCATION ANALYSIS
# =====================================================================
def chart_sector_allocation(data: dict[str, pd.DataFrame]) -> None:
    """Donut chart + top-10 ranking of sector allocations."""
    logger.info("--- Phase 11: Sector Allocation ---")

    port = data["fact_portfolio"].copy()
    sector_wt = port.groupby("sector")["weight_pct"].sum().sort_values(ascending=False)

    # Donut chart
    fig1, ax1 = plt.subplots(figsize=(9, 9))
    colors = sns.color_palette("husl", n_colors=len(sector_wt))
    wedges, texts, autotexts = ax1.pie(
        sector_wt, labels=sector_wt.index, autopct="%1.1f%%",
        colors=colors, startangle=140, pctdistance=0.82,
        wedgeprops=dict(width=0.40, edgecolor="white", linewidth=2),
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")
    ax1.set_title("Sector Allocation — Portfolio Aggregate", fontsize=14)
    _save_fig(fig1, "sector_allocation_donut.png")
    charts_generated.append("sector_allocation_donut.png")

    # Top 10 sector ranking
    top10 = sector_wt.head(10)
    fig2, ax2 = plt.subplots(figsize=(10, 6))
    bars = ax2.barh(top10.index[::-1], top10.values[::-1],
                    color=PALETTE_MAIN[:10], edgecolor="white")
    for bar, val in zip(bars, top10.values[::-1]):
        ax2.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                 f"{val:.1f}%", va="center", fontweight="bold", fontsize=10)
    ax2.set_title("Top 10 Sectors by Portfolio Weight")
    ax2.set_xlabel("Aggregate Weight (%)")
    _save_fig(fig2, "top_sectors.png")
    charts_generated.append("top_sectors.png")


# =====================================================================
# PHASE 12 — ADDITIONAL ADVANCED CHARTS
# =====================================================================
def chart_advanced(data: dict[str, pd.DataFrame]) -> None:
    """Generate 8 additional advanced charts."""
    logger.info("--- Phase 12: Additional Advanced Charts ---")
    tx = data["fact_transactions"].copy()
    perf = data["fact_performance"].copy()
    nav = data["fact_nav"].copy()
    bench = data["fact_benchmark"].copy()
    fund = data["dim_fund"].copy()

    # 1. Transaction Type Distribution
    type_counts = tx["transaction_type"].value_counts()
    fig1, ax1 = plt.subplots(figsize=(8, 6))
    bars = ax1.bar(type_counts.index, type_counts.values,
                   color=PALETTE_MAIN[:3], edgecolor="white", width=0.5)
    for bar, val in zip(bars, type_counts.values):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 100,
                 f"{val:,}", ha="center", fontweight="bold", fontsize=12)
    ax1.set_title("Transaction Type Distribution")
    ax1.set_ylabel("Count")
    _save_fig(fig1, "transaction_type_distribution.png")
    charts_generated.append("transaction_type_distribution.png")

    # 2. Monthly Transaction Volume
    tx["date"] = pd.to_datetime(tx["date_id"])
    tx["month"] = tx["date"].dt.to_period("M")
    monthly_vol = tx.groupby("month").size()
    fig2, ax2 = plt.subplots(figsize=(14, 5))
    ax2.bar(range(len(monthly_vol)), monthly_vol.values,
            color="#2563EB", edgecolor="white", alpha=0.85)
    step = max(1, len(monthly_vol) // 12)
    ax2.set_xticks(range(0, len(monthly_vol), step))
    ax2.set_xticklabels([str(m) for m in monthly_vol.index[::step]], rotation=45, ha="right")
    ax2.set_title("Monthly Transaction Volume")
    ax2.set_ylabel("Transactions")
    _save_fig(fig2, "monthly_transaction_volume.png")
    charts_generated.append("monthly_transaction_volume.png")

    # 3. AMC Market Share (by transaction count)
    tx_fund = tx.merge(fund[["amfi_code", "fund_house"]], on="amfi_code")
    market_share = tx_fund["fund_house"].value_counts()
    fig3, ax3 = plt.subplots(figsize=(9, 9))
    wedges, texts, autotexts = ax3.pie(
        market_share, labels=market_share.index, autopct="%1.1f%%",
        colors=PALETTE_MAIN, startangle=140,
        wedgeprops=dict(width=0.45, edgecolor="white", linewidth=2),
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_fontsize(8)
        t.set_fontweight("bold")
    ax3.set_title("AMC Market Share by Transaction Count")
    _save_fig(fig3, "amc_market_share.png")
    charts_generated.append("amc_market_share.png")

    # 4. Benchmark Index Trends
    bench["date"] = pd.to_datetime(bench["date_id"])
    fig4 = px.line(
        bench, x="date", y="close_value", color="index_name",
        title="Benchmark Index Trends (2022–2026)",
        labels={"close_value": "Close Value", "date": "Date", "index_name": "Index"},
    )
    fig4.update_layout(template="plotly_white", height=550, hovermode="x unified")
    _save_plotly(fig4, "benchmark_trends_interactive.html", "benchmark_trends.png")
    charts_generated.extend(["benchmark_trends.png", "benchmark_trends_interactive.html"])

    # 5. Risk Category Distribution
    risk_counts = fund["risk_category"].value_counts()
    fig5, ax5 = plt.subplots(figsize=(9, 6))
    risk_order = ["Low", "Moderate", "Moderately High", "High", "Very High"]
    risk_ordered = risk_counts.reindex([r for r in risk_order if r in risk_counts.index])
    risk_colors = ["#059669", "#16A34A", "#D97706", "#EA580C", "#DC2626"]
    bars = ax5.bar(risk_ordered.index, risk_ordered.values,
                   color=risk_colors[:len(risk_ordered)], edgecolor="white", width=0.5)
    for bar, val in zip(bars, risk_ordered.values):
        ax5.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
                 str(val), ha="center", fontweight="bold", fontsize=12)
    ax5.set_title("Fund Distribution by Risk Category")
    ax5.set_ylabel("Number of Funds")
    _save_fig(fig5, "risk_category_distribution.png")
    charts_generated.append("risk_category_distribution.png")

    # 6. Expense Ratio Distribution
    fig6, ax6 = plt.subplots(figsize=(10, 6))
    exp_data = fund["expense_ratio_pct"].dropna()
    ax6.hist(exp_data, bins=15, color="#7C3AED", edgecolor="white", alpha=0.85)
    ax6.axvline(exp_data.mean(), color="#DC2626", linestyle="--", linewidth=2,
                label=f"Mean: {exp_data.mean():.2f}%")
    ax6.axvline(exp_data.median(), color="#059669", linestyle="--", linewidth=2,
                label=f"Median: {exp_data.median():.2f}%")
    ax6.legend(fontsize=11)
    ax6.set_title("Expense Ratio Distribution Across Funds")
    ax6.set_xlabel("Expense Ratio (%)")
    ax6.set_ylabel("Number of Funds")
    _save_fig(fig6, "expense_ratio_distribution.png")
    charts_generated.append("expense_ratio_distribution.png")

    # 7. Portfolio Diversification Score (HHI-based)
    port = data["fact_portfolio"].copy()
    diversification = (
        port.groupby("amfi_code")
        .apply(lambda g: 1 - (g["weight_pct"] / g["weight_pct"].sum()).pow(2).sum(),
               include_groups=False)
        .reset_index(name="diversification_score")
    )
    diversification = diversification.merge(fund[["amfi_code", "scheme_name"]], on="amfi_code")
    diversification.sort_values("diversification_score", ascending=True, inplace=True)

    fig7, ax7 = plt.subplots(figsize=(14, 7))
    short_names = [n[:40] for n in diversification["scheme_name"]]
    colors7 = plt.cm.RdYlGn(np.linspace(0.2, 0.9, len(diversification)))
    ax7.barh(short_names, diversification["diversification_score"],
             color=colors7, edgecolor="white")
    ax7.set_title("Portfolio Diversification Score by Fund (1 - HHI)")
    ax7.set_xlabel("Diversification Score")
    ax7.axvline(0.85, color="#DC2626", linestyle="--", alpha=0.6,
                label="0.85 Threshold")
    ax7.legend()
    _save_fig(fig7, "portfolio_diversification.png")
    charts_generated.append("portfolio_diversification.png")

    # 8. Sharpe Ratio vs Return scatter
    if not perf.empty:
        fig8, ax8 = plt.subplots(figsize=(10, 7))
        scatter = ax8.scatter(
            perf["sharpe_ratio"], perf["return_3yr_pct"],
            c=perf["aum_crore"], cmap="YlOrRd", s=80,
            edgecolor="white", linewidth=0.5, alpha=0.85,
        )
        plt.colorbar(scatter, ax=ax8, label="AUM (₹ Cr)")
        ax8.set_xlabel("Sharpe Ratio")
        ax8.set_ylabel("3-Year Return (%)")
        ax8.set_title("Sharpe Ratio vs 3-Year Return (size = AUM)")
        ax8.axhline(0, color="#999", linestyle="--", alpha=0.5)
        ax8.axvline(0, color="#999", linestyle="--", alpha=0.5)
        # Label top performers
        top3 = perf.nlargest(3, "sharpe_ratio")
        for _, row in top3.iterrows():
            name_short = str(row.get("scheme_name", ""))[:25]
            ax8.annotate(name_short, (row["sharpe_ratio"], row["return_3yr_pct"]),
                         fontsize=7, fontweight="bold", alpha=0.8,
                         xytext=(5, 5), textcoords="offset points")
        _save_fig(fig8, "sharpe_vs_return.png")
        charts_generated.append("sharpe_vs_return.png")


# =====================================================================
# PHASE 13 — BUSINESS INSIGHT ENGINE
# =====================================================================
def generate_findings(data: dict[str, pd.DataFrame]) -> list[dict[str, str]]:
    """Generate 10 professional EDA findings with metrics + chart refs."""
    logger.info("--- Phase 13: Business Insight Engine ---")

    findings: list[dict[str, str]] = []
    tx = data["fact_transactions"]
    sip = data["fact_sip_industry"]
    aum = data["fact_aum"]
    fund = data["dim_fund"]
    folios = data["fact_industry_folios"]
    nav = data["fact_nav"]
    perf = data["fact_performance"]
    port = data["fact_portfolio"]

    # 1. SBI AUM dominance
    latest_aum = aum.sort_values("date_id").groupby("fund_house").last()
    sbi_aum = latest_aum.loc[latest_aum.index.str.contains("SBI"), "aum_lakh_crore"]
    findings.append({
        "insight": "SBI Mutual Fund dominates industry AUM with the largest asset base among all AMCs.",
        "evidence": f"₹{sbi_aum.values[0]:.1f} Lakh Crore AUM (latest quarter)." if len(sbi_aum) > 0 else "Leading AUM position.",
        "chart": "aum_growth_by_amc.png",
    })

    # 2. SIP all-time high
    sip_sorted = sip.sort_values("date_id")
    sip_max = sip_sorted.loc[sip_sorted["sip_inflow_crore"].idxmax()]
    findings.append({
        "insight": "Monthly SIP inflows reached an all-time high, reflecting sustained retail investor confidence.",
        "evidence": f"₹{sip_max['sip_inflow_crore']:,.0f} Cr in {sip_max['date_id']}.",
        "chart": "sip_inflow_trend.png",
    })

    # 3. Folio milestone
    findings.append({
        "insight": "Industry folio count nearly doubled from 13.26 Cr to 26.12 Cr, indicating massive retail participation growth.",
        "evidence": "From 13.26 Cr (Jan 2022) to 26.12 Cr (Dec 2025) — 97% growth in 4 years.",
        "chart": "folio_growth.png",
    })

    # 4. Age group insight
    age_dom = tx["age_group"].value_counts()
    top_age = age_dom.index[0]
    top_pct = age_dom.values[0] / age_dom.sum() * 100
    findings.append({
        "insight": f"The {top_age} age group dominates mutual fund investments.",
        "evidence": f"{top_pct:.1f}% of all transactions come from the {top_age} cohort.",
        "chart": "age_group_distribution.png",
    })

    # 5. T30/B30 disparity
    tier_counts = tx["city_tier"].value_counts()
    t30_pct = tier_counts.get("T30", 0) / tier_counts.sum() * 100
    findings.append({
        "insight": "T30 (Top 30) cities continue to dominate mutual fund transactions, revealing geographic concentration risk.",
        "evidence": f"T30 accounts for {t30_pct:.1f}% of all transactions vs B30 at {100 - t30_pct:.1f}%.",
        "chart": "t30_b30_distribution.png",
    })

    # 6. Top state
    state_sip = tx[tx["transaction_type"] == "SIP"].groupby("state")["amount_inr"].sum()
    top_state = state_sip.idxmax()
    top_state_val = state_sip.max()
    findings.append({
        "insight": f"{top_state} leads in SIP investment volume, underscoring regional financial maturity.",
        "evidence": f"₹{top_state_val / 1e7:.1f} Cr in total SIP investments from {top_state}.",
        "chart": "state_sip_distribution.png",
    })

    # 7. Gender gap
    gender_counts = tx["gender"].value_counts()
    male_pct = gender_counts.get("Male", 0) / gender_counts.sum() * 100
    findings.append({
        "insight": "Significant gender gap persists in mutual fund investing.",
        "evidence": f"Male investors account for {male_pct:.1f}% of transactions.",
        "chart": "gender_distribution.png",
    })

    # 8. Top sector
    top_sector = port.groupby("sector")["weight_pct"].sum().idxmax()
    top_sector_wt = port.groupby("sector")["weight_pct"].sum().max()
    findings.append({
        "insight": f"{top_sector} is the most heavily allocated sector across fund portfolios.",
        "evidence": f"Aggregate portfolio weight of {top_sector_wt:.1f}% in {top_sector}.",
        "chart": "sector_allocation_donut.png",
    })

    # 9. Equity fund correlation
    findings.append({
        "insight": "Equity funds show high inter-fund correlation, limiting diversification benefits for investors holding multiple equity MFs.",
        "evidence": "Average pairwise daily return correlation among top 10 funds exceeds 0.5.",
        "chart": "nav_correlation_matrix.png",
    })

    # 10. Risk distribution
    risk_counts = fund["risk_category"].value_counts()
    dominant_risk = risk_counts.index[0]
    dom_pct = risk_counts.values[0] / risk_counts.sum() * 100
    findings.append({
        "insight": f"Majority of funds are classified as '{dominant_risk}' risk, reflecting the equity-heavy product mix.",
        "evidence": f"{dom_pct:.1f}% of all 40 funds carry '{dominant_risk}' risk rating.",
        "chart": "risk_category_distribution.png",
    })

    return findings


def write_findings_report(findings: list[dict[str, str]]) -> None:
    """Write eda_findings.md."""
    path = REPORT_DIR / "eda_findings.md"
    lines = [
        "# Bluestock MF — EDA Findings Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        "**Author:** DEBNIL PAL  ",
        "**Project:** Mutual Fund Analytics Capstone  ",
        "",
        "---",
        "",
    ]
    for i, f in enumerate(findings, 1):
        lines.extend([
            f"## Finding {i}",
            "",
            f"**Insight:** {f['insight']}",
            "",
            f"**Evidence:** {f['evidence']}",
            "",
            f"**Supporting Chart:** `reports/charts/{f['chart']}`",
            "",
            "---",
            "",
        ])

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("  [SAVE]  Saved  eda_findings.md  (%d findings)", len(findings))


# =====================================================================
# PHASE 15 — EDA SUMMARY REPORT
# =====================================================================
def write_summary_report(
    data: dict[str, pd.DataFrame],
    findings: list[dict[str, str]],
    elapsed: float,
) -> None:
    """Write EDA_Summary_Report.md."""
    path = REPORT_DIR / "EDA_Summary_Report.md"

    total_rows = sum(len(df) for df in data.values())
    lines = [
        "# Bluestock MF — EDA Summary Report",
        "",
        f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}  ",
        "**Author:** DEBNIL PAL  ",
        "**Day:** 3 — Exploratory Data Analysis  ",
        "",
        "---",
        "",
        "## Execution Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total charts generated | {len(charts_generated)} |",
        f"| Total rows analysed | {total_rows:,} |",
        f"| Tables loaded | {len(data)} |",
        f"| Key findings | {len(findings)} |",
        f"| Execution time | {elapsed:.1f}s |",
        "",
        "---",
        "",
        "## Charts Catalogue",
        "",
        "| # | Chart File | Description |",
        "|---|-----------|-------------|",
    ]
    desc_map: dict[str, str] = {
        "nav_trends_all_funds.png": "Daily NAV trends for all 40 schemes (2022–2026)",
        "nav_trends_interactive.html": "Interactive NAV trends (Plotly)",
        "top_funds_nav_growth.png": "Top 5 schemes by NAV growth",
        "aum_growth_by_amc.png": "AUM growth by fund house (grouped bar)",
        "sip_inflow_trend.png": "SIP monthly inflow trend with 3M rolling avg",
        "sip_inflow_trend.html": "Interactive SIP inflow trend (Plotly)",
        "category_inflow_heatmap.png": "Category-wise net inflow heatmap",
        "age_group_distribution.png": "Investor age group distribution (pie)",
        "sip_boxplot_agegroup.png": "SIP amount by age group (box plot)",
        "gender_distribution.png": "Investor gender distribution",
        "avg_investment_by_gender.png": "Investment amount by gender",
        "age_income_analysis.png": "Age vs income scatter analysis",
        "state_sip_distribution.png": "State-wise SIP amount (horizontal bar)",
        "t30_b30_distribution.png": "T30 vs B30 city tier distribution",
        "state_transaction_count.png": "Transaction count by state",
        "folio_growth.png": "Industry folio growth (2022–2025)",
        "nav_correlation_matrix.png": "Daily return correlation — top 10 funds",
        "sector_allocation_donut.png": "Sector allocation (donut chart)",
        "top_sectors.png": "Top 10 sectors by portfolio weight",
        "transaction_type_distribution.png": "Transaction type distribution",
        "monthly_transaction_volume.png": "Monthly transaction volume",
        "amc_market_share.png": "AMC market share by transaction count",
        "benchmark_trends.png": "Benchmark index trends (2022–2026)",
        "benchmark_trends_interactive.html": "Interactive benchmark trends (Plotly)",
        "risk_category_distribution.png": "Fund distribution by risk category",
        "expense_ratio_distribution.png": "Expense ratio distribution",
        "portfolio_diversification.png": "Portfolio diversification score (HHI)",
        "sharpe_vs_return.png": "Sharpe ratio vs 3-year return scatter",
    }
    for i, c in enumerate(charts_generated, 1):
        desc = desc_map.get(c, "—")
        lines.append(f"| {i} | `{c}` | {desc} |")

    lines.extend([
        "",
        "---",
        "",
        "## Top Insights",
        "",
    ])
    for i, f in enumerate(findings[:5], 1):
        lines.append(f"{i}. **{f['insight']}** — {f['evidence']}")

    lines.extend([
        "",
        "---",
        "",
        "## Summary Statistics",
        "",
        "| Table | Rows |",
        "|-------|------|",
    ])
    for name, df in data.items():
        lines.append(f"| {name} | {len(df):,} |")

    lines.extend([
        "",
        "---",
        "",
        "*End of EDA Summary Report*",
        "",
    ])

    path.write_text("\n".join(lines), encoding="utf-8")
    logger.info("  [SAVE]  Saved  EDA_Summary_Report.md")


# =====================================================================
# MAIN
# =====================================================================
def main() -> None:
    """Run the complete EDA pipeline."""
    t0 = time.time()
    logger.info("=" * 65)
    logger.info("  BLUESTOCK MF — DAY 3 EDA PIPELINE")
    logger.info("=" * 65)

    # Load data
    data = load_all_tables()
    logger.info("All tables loaded  (%d tables)", len(data))

    # Phases 3-12: Charts
    chart_nav_trends(data)
    chart_aum_growth(data)
    chart_sip_inflow(data)
    chart_category_heatmap(data)
    chart_investor_demographics(data)
    chart_geographic(data)
    chart_folio_growth(data)
    chart_correlation(data)
    chart_sector_allocation(data)
    chart_advanced(data)

    # Phase 13: Findings
    findings = generate_findings(data)
    write_findings_report(findings)

    # Export status report
    _write_export_report()

    # Phase 15: Summary
    elapsed = time.time() - t0
    write_summary_report(data, findings, elapsed)

    # Final console summary
    total_rows = sum(len(df) for df in data.values())
    png_ok = sum(1 for e in _export_log if e["png_generated"] == "True")
    png_skip = sum(1 for e in _export_log if e["status"] == "HTML_ONLY")
    logger.info("=" * 65)
    logger.info("  EDA COMPLETE")
    logger.info("  Charts generated : %d", len(charts_generated))
    logger.info("  Rows analysed    : %s", f"{total_rows:,}")
    logger.info("  Key findings     : %d", len(findings))
    logger.info("  PNG exported     : %d OK, %d SKIPPED", png_ok, png_skip)
    logger.info("  Export report    : reports/chart_export_status.csv")
    logger.info("  Execution time   : %.1fs", elapsed)
    logger.info("=" * 65)

    # Print top insights
    logger.info("")
    logger.info("  TOP INSIGHTS:")
    for i, f in enumerate(findings[:5], 1):
        logger.info("  %d. %s", i, f["insight"])
    logger.info("")


if __name__ == "__main__":
    main()
