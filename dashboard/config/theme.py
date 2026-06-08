"""
Bluestock MF Dashboard -- Design System & Theme Configuration
=============================================================
Single Light Fintech Theme.
"""

# ── Colour Palette ──────────────────────────────────────────
PRIMARY      = "#0A4D8C"   # Deep fintech blue
SECONDARY    = "#00B894"   # Emerald green
ACCENT       = "#38BDF8"   # Sky accent
BACKGROUND   = "#F8FAFC"   # Off-white bg
CARD_BG      = "#FFFFFF"   # Card surfaces
TEXT_PRIMARY  = "#1F2937"   # Near-black text
TEXT_MUTED    = "#6B7280"   # Muted/secondary text
BORDER       = "#E5E7EB"   # Light border
SUCCESS      = "#10B981"   # Green
WARNING      = "#F59E0B"   # Amber
DANGER       = "#EF4444"   # Red
INFO         = "#3B82F6"   # Blue

# Category-based palette for charts
CHART_PALETTE = [
    "#0A4D8C", "#00B894", "#E17055", "#6C5CE7",
    "#FDCB6E", "#0984E3", "#D63031", "#00CEC9",
    "#E84393", "#2D3436", "#636E72", "#74B9FF",
    "#55EFC4", "#FAB1A0", "#A29BFE", "#FD79A8",
]

# Tier colours for scorecard
TIER_COLORS = {
    "Elite":   "#1B5E20",
    "Strong":  "#2E7D32",
    "Average": "#F57F17",
    "Weak":    "#C62828",
}

# ── Plotly Layout Template ──────────────────────────────────
PLOTLY_LAYOUT = dict(
    font=dict(family="Inter, -apple-system, sans-serif", color=TEXT_PRIMARY),
    paper_bgcolor=CARD_BG,
    plot_bgcolor=CARD_BG,
    margin=dict(l=40, r=20, t=50, b=40),
    title_font=dict(size=16, color=TEXT_PRIMARY),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.20,
        xanchor="center", x=0.5, font_size=10,
    ),
    xaxis=dict(gridcolor="#F0F0F0", linecolor=BORDER),
    yaxis=dict(gridcolor="#F0F0F0", linecolor=BORDER),
    hoverlabel=dict(bgcolor=CARD_BG, font_size=12),
    colorway=CHART_PALETTE,
)


# ── Custom CSS ──────────────────────────────────────────────
CUSTOM_CSS = """
<style>
/* ── Global ──────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

/* Hide Streamlit branding */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

/* ── KPI Cards ───────────────────────────────────────── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 12px;
    padding: 20px 24px;
    text-align: center;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
}
.kpi-label {
    font-size: 12px;
    font-weight: 600;
    color: #6B7280;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}
.kpi-value {
    font-size: 28px;
    font-weight: 700;
    color: #0A4D8C;
    line-height: 1.2;
}
.kpi-delta {
    font-size: 12px;
    font-weight: 500;
    margin-top: 4px;
}
.kpi-delta.positive { color: #10B981; }
.kpi-delta.negative { color: #EF4444; }

/* ── Section Headers ─────────────────────────────────── */
.section-header {
    font-size: 18px;
    font-weight: 700;
    color: #0A4D8C;
    border-bottom: 3px solid #00B894;
    padding-bottom: 8px;
    margin: 24px 0 16px 0;
}

/* ── Spotlight Card ──────────────────────────────────── */
.spotlight-card {
    background: linear-gradient(135deg, #0A4D8C 0%, #1565C0 100%);
    border-radius: 14px;
    padding: 24px 28px;
    color: #FFFFFF;
    box-shadow: 0 4px 16px rgba(10,77,140,0.25);
}
.spotlight-title {
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
    opacity: 0.85;
    margin-bottom: 8px;
}
.spotlight-fund {
    font-size: 20px;
    font-weight: 700;
    margin-bottom: 12px;
    line-height: 1.3;
}
.spotlight-metric {
    font-size: 13px;
    opacity: 0.9;
    line-height: 1.6;
}

/* ── Insight Box ─────────────────────────────────────── */
.insight-box {
    background: #EEF7FF;
    border-left: 4px solid #0A4D8C;
    border-radius: 0 8px 8px 0;
    padding: 14px 18px;
    margin: 8px 0;
    font-size: 13px;
    color: #1F2937;
    line-height: 1.5;
}

/* ── Status Bar ──────────────────────────────────────── */
.status-bar {
    background: #F0FDF4;
    border: 1px solid #BBF7D0;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 12px;
    color: #166534;
    display: flex;
    gap: 24px;
    margin-bottom: 16px;
}

/* ── Risk Badges ─────────────────────────────────────── */
.risk-high { background: #FEE2E2; color: #991B1B; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.risk-med  { background: #FEF3C7; color: #92400E; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }
.risk-low  { background: #D1FAE5; color: #065F46; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600; }

/* ── Tabs ────────────────────────────────────────────── */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 6px 6px 0 0;
    padding: 8px 20px;
    font-weight: 600;
}
</style>
"""


# ── Helper: render a KPI card ───────────────────────────────
def kpi_card_html(label: str, value: str, delta: str = "", delta_dir: str = "") -> str:
    """Return HTML for a single KPI card."""
    delta_html = ""
    if delta:
        cls = "positive" if delta_dir == "up" else ("negative" if delta_dir == "down" else "")
        arrow = "&#9650; " if delta_dir == "up" else ("&#9660; " if delta_dir == "down" else "")
        delta_html = f'<div class="kpi-delta {cls}">{arrow}{delta}</div>'
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {delta_html}
    </div>
    """


def spotlight_card_html(fund_name: str, score: float, sharpe: float,
                        cagr_3yr: float, category: str) -> str:
    """Return HTML for the top-fund spotlight card."""
    return f"""
    <div class="spotlight-card">
        <div class="spotlight-title">Top Ranked Fund</div>
        <div class="spotlight-fund">{fund_name}</div>
        <div class="spotlight-metric">
            Composite Score: <b>{score:.1f}</b> &nbsp;|&nbsp;
            Sharpe: <b>{sharpe:.2f}</b> &nbsp;|&nbsp;
            3Y CAGR: <b>{cagr_3yr:.1f}%</b><br>
            Category: <b>{category}</b>
        </div>
    </div>
    """


def status_bar_html(db_status: str, last_refresh: str,
                    records: int, filters: str = "None") -> str:
    """Return HTML for the data-health status bar."""
    return f"""
    <div class="status-bar">
        <span><b>DB:</b> {db_status}</span>
        <span><b>Refreshed:</b> {last_refresh}</span>
        <span><b>Records:</b> {records:,}</span>
        <span><b>Filters:</b> {filters}</span>
    </div>
    """


def insight_html(text: str) -> str:
    """Return HTML for an insight box."""
    return f'<div class="insight-box">{text}</div>'
