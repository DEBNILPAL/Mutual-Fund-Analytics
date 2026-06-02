# 📊 Bluestock Fintech — Mutual Fund Analytics Capstone

> Production-grade mutual fund data analytics pipeline built with Python, Pandas, and the MFAPI. This capstone project ingests, validates, profiles, and analyzes Indian mutual fund data across 10+ dimensions.

---

## 🏗️ Project Overview

This project is part of the **Bluestock Fintech Mutual Fund Analytics Capstone**. The goal is to build a complete end-to-end analytics platform covering:

- **Data Ingestion** — Automated discovery, loading, and profiling of 10 raw datasets
- **Data Quality** — Missing values, duplicates, blank columns, type issues
- **Fund Master Analysis** — Scheme distribution across AMCs, categories, and risk levels
- **AMFI Validation** — Cross-referencing fund master codes against NAV history
- **Live NAV Fetch** — Real-time NAV data from MFAPI for 6 large-cap schemes
- **Performance Analytics** — Returns, risk metrics, Sharpe ratios *(coming in Day 2+)*
- **Investor Behavior** — Transaction patterns, SIP vs. Lumpsum, demographics *(coming in Day 2+)*
- **Dashboard** — Interactive Plotly/Streamlit visualizations *(coming in Day 3+)*

---

## 📁 Folder Structure

```
bluestock_mf_capstone/
│
├── data/
│   ├── raw/                          # Original CSV datasets + live NAV downloads
│   │   ├── 01_fund_master.csv
│   │   ├── 02_nav_history.csv
│   │   ├── 03_aum_by_fund_house.csv
│   │   ├── 04_monthly_sip_inflows.csv
│   │   ├── 05_category_inflows.csv
│   │   ├── 06_industry_folio_count.csv
│   │   ├── 07_scheme_performance.csv
│   │   ├── 08_investor_transactions.csv
│   │   ├── 09_portfolio_holdings.csv
│   │   ├── 10_benchmark_indices.csv
│   │   ├── nav_125497.csv            # Live NAV (per-scheme)
│   │   └── all_live_nav.csv          # Combined live NAV
│   ├── processed/                    # Cleaned outputs & reports
│   │   ├── data_quality_summary.csv
│   │   ├── data_quality_summary.txt
│   │   ├── fund_master_profile.csv
│   │   └── amfi_validation_report.csv
│   └── db/                           # SQLite databases (future)
│
├── scripts/
│   ├── data_ingestion.py             # Full ingestion + profiling pipeline
│   └── live_nav_fetch.py             # MFAPI NAV downloader
│
├── notebooks/                        # Jupyter analysis notebooks (future)
├── sql/                              # SQL queries & schema definitions (future)
├── logs/                             # Execution logs
│   ├── data_ingestion.log
│   └── nav_fetch.log
├── dashboard/                        # Dashboard app (future)
├── reports/                          # Generated reports (future)
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.10+ |
| Data Processing | Pandas, NumPy, SciPy |
| Visualization | Matplotlib, Seaborn, Plotly |
| API Client | Requests |
| Database | SQLAlchemy (SQLite) |
| Notebooks | Jupyter |
| Version Control | Git + GitHub |

---

## 📦 Dataset Description

| # | File | Description | Key Columns |
|---|------|-------------|-------------|
| 01 | `fund_master.csv` | Scheme registry with AMC, category, risk, benchmarks | `amfi_code`, `fund_house`, `category`, `risk_category` |
| 02 | `nav_history.csv` | Daily NAV time series (2022–2025) | `amfi_code`, `date`, `nav` |
| 03 | `aum_by_fund_house.csv` | AUM snapshots by fund house | `date`, `fund_house`, `aum_crore` |
| 04 | `monthly_sip_inflows.csv` | Industry-level monthly SIP flows | `month`, `sip_amount_crore` |
| 05 | `category_inflows.csv` | Category-wise inflow/outflow data | `category`, `net_inflow_crore` |
| 06 | `industry_folio_count.csv` | Total folio (account) counts | `year`, `folio_count_crore` |
| 07 | `scheme_performance.csv` | Return, risk, and rating metrics | `amfi_code`, `return_1yr_pct`, `sharpe_ratio` |
| 08 | `investor_transactions.csv` | 32K+ investor transactions | `investor_id`, `transaction_type`, `amount_inr` |
| 09 | `portfolio_holdings.csv` | Stock-level portfolio breakdowns | `amfi_code`, `stock_symbol`, `weight_pct` |
| 10 | `benchmark_indices.csv` | NIFTY/BSE benchmark time series | `date`, `index_name`, `close` |

---

## 🚀 Installation Steps

### 1. Clone the Repository

```powershell
git clone https://github.com/<your-username>/bluestock-mf-capstone.git
cd bluestock-mf-capstone
```

### 2. Create Virtual Environment

```powershell
python -m venv venv
.\venv\Scripts\Activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

---

## ▶️ Running Data Ingestion

```powershell
python scripts/data_ingestion.py
```

**What it does:**
- Discovers all CSVs in `data/raw/`
- Loads and prints schema details (rows, columns, dtypes, head)
- Runs quality profiling (missing values, duplicates, blank columns)
- Performs Fund Master analysis (schemes per AMC, category, risk)
- Validates AMFI codes between fund master and NAV history
- Exports results to `data/processed/`

**Outputs:**
- `data/processed/data_quality_summary.csv`
- `data/processed/data_quality_summary.txt`
- `data/processed/fund_master_profile.csv`
- `data/processed/amfi_validation_report.csv`
- `logs/data_ingestion.log`

---

## ▶️ Running Live NAV Fetch

```powershell
python scripts/live_nav_fetch.py
```

**What it does:**
- Fetches live NAV data for 6 large-cap schemes via MFAPI
- Handles connection errors, timeouts, and malformed responses
- Saves individual scheme CSVs + combined dataset

**Outputs:**
- `data/raw/nav_125497.csv` through `nav_120841.csv`
- `data/raw/all_live_nav.csv`
- `logs/nav_fetch.log`

---

## 📤 Expected Outputs

After running both scripts, your `data/processed/` directory will contain:

```
data_quality_summary.csv      — Quality metrics for all 10 datasets
data_quality_summary.txt      — Human-readable summary report
fund_master_profile.csv       — Scheme distribution analysis
amfi_validation_report.csv    — AMFI code cross-validation results
```

---

## 🔄 Git Workflow

```powershell
# Initialize repository
git init
git remote add origin https://github.com/<your-username>/bluestock-mf-capstone.git

# Stage and commit Day 1
git add .
git commit -m "Day 1: Data ingestion, quality profiling, AMFI validation, live NAV fetch"

# Push to GitHub
git branch -M main
git push -u origin main
```

---

## 📝 License

This project is developed for educational purposes as part of the Bluestock Fintech Capstone Program.

---

## 👤 Author

Built with ❤️ by the **Bluestock Fintech Analytics Team**
