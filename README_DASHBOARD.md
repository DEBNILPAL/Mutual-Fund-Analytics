# Bluestock Mutual Fund Analytics Dashboard

Production-grade interactive analytics dashboard for Indian Mutual Fund industry analysis.

**Day 5 Capstone Deliverable** | Bluestock Fintech

---

## Features

### 4-Page Dashboard
1. **Market Overview** -- Industry AUM, SIP trends, folio growth, category heatmap, Top 10 AMCs
2. **Fund Performance & Risk** -- Sharpe/Sortino rankings, Alpha-Beta scatter, CAGR heatmap, fund comparison tool, benchmark comparison
3. **Investor Demographics** -- Age/gender/income distributions, SIP vs Lumpsum, state-wise analysis, T30/B30 split
4. **Portfolio & Benchmark Analytics** -- Sector allocation, top holdings, growth-of-Rs.100, rolling correlation, concentration risk table

### Executive Dashboard
- 6 KPI cards (AUM, Schemes, Investors, Transactions, SIP Inflow, Best Score)
- Top Fund Spotlight card with composite score
- Data health status bar on every page

### Advanced Features
- Global filters (AMC, Category, Risk)
- Fund A vs Fund B comparison with radar chart
- Benchmark quick comparison with growth chart
- Dynamic insight engine (auto-generated observations)
- CSV export on every page
- Cross-filtering across charts

### Power BI Package
- 17 CSV dataset exports
- Complete DAX measures
- Theme configuration JSON
- Visual layout blueprint

---

## Architecture

```
dashboard/
  app.py                    # Main entry point
  .streamlit/config.toml    # Streamlit theme config
  config/
    theme.py                # Design system (colours, CSS, templates)
  utils/
    database.py             # Cached data access layer (16 functions)
    charts.py               # Reusable Plotly chart builders (9 types)
    insights.py             # Dynamic insight generator (4 page engines)
  pages/
    1_Market_Overview.py    # Page 1: Industry overview
    2_Fund_Performance.py   # Page 2: Performance & risk analytics
    3_Investor_Demographics.py  # Page 3: Investor analysis
    4_Portfolio_Analytics.py    # Page 4: Portfolio & benchmark

powerbi/
  PowerBI_Setup_Guide.md    # Complete Power BI blueprint
  powerbi_dataset_exports/  # 17 CSV files for Power BI import
```

---

## Data Sources

| Source | Type | Records |
|--------|------|---------|
| `data/db/bluestock_mf.db` | SQLite Warehouse | 88,839 rows |
| `data/processed/*.csv` | Day 4 Analytics | 8 files |

### Database Tables
- `dim_fund` (40 funds) -- Fund metadata
- `fact_nav` (46,000) -- Daily NAV history
- `fact_transactions` (32,778) -- Investor transactions
- `fact_performance` (40) -- Performance metrics
- `fact_aum` (90) -- AUM by AMC
- `fact_sip_industry` (48) -- SIP trends
- `fact_category_inflows` (144) -- Category flows
- `fact_industry_folios` (21) -- Folio growth
- `fact_portfolio` (322) -- Holdings data
- `fact_benchmark` (8,050) -- Index data

---

## How to Run

### Prerequisites
```bash
pip install streamlit plotly pandas numpy
```

### Launch Dashboard
```bash
cd "d:\Downloads\BlueStock Project\project_1"
streamlit run dashboard/app.py
```

The dashboard will open at `http://localhost:8501`.

### Generate Power BI Exports
```bash
python scripts/export_powerbi.py
```

---

## Design System

| Token | Value | Usage |
|-------|-------|-------|
| Primary | `#0A4D8C` | Headers, primary actions |
| Secondary | `#00B894` | Accents, success indicators |
| Accent | `#38BDF8` | Highlights |
| Background | `#F8FAFC` | Page background |
| Card | `#FFFFFF` | Card surfaces |
| Text | `#1F2937` | Primary text |

### Chart Palette
16-colour fintech palette for consistent visualisation across all pages.

---

## Performance

- All database queries cached with `@st.cache_data(ttl=600)`
- Data accessed exclusively through `dashboard/utils/database.py`
- No direct SQL in page files
- Target load time: < 5 seconds

---

## Dependencies

```
streamlit >= 1.58.0
plotly >= 5.0
pandas >= 2.0
numpy >= 1.23
```

---

## Screenshots

Screenshots available in `dashboard/screenshots/`:
- `market_overview.png`
- `fund_performance.png`
- `investor_demographics.png`
- `portfolio_analytics.png`

---

## Project Timeline

| Day | Deliverable | Status |
|-----|-------------|--------|
| Day 1 | ETL Pipeline | Complete |
| Day 2 | Data Warehouse | Complete |
| Day 3 | EDA | Complete |
| Day 4 | Performance Analytics | Complete |
| **Day 5** | **Interactive Dashboard** | **Complete** |

---

## Author

**DEBNIL PAL** | Bluestock Fintech Capstone Project
