# Power BI Dashboard Setup Guide

## Bluestock Mutual Fund Analytics

Complete blueprint to build the Power BI version of the Bluestock MF Analytics Dashboard.

---

## 1. Data Import

### Dataset Location

All CSV files are in `powerbi/powerbi_dataset_exports/`.

### Import Steps

1. Open Power BI Desktop
2. Click **Get Data > Text/CSV**
3. Import ALL 17 CSV files from the exports folder
4. For each file, verify column data types in the **Transform Data** editor

### Files to Import

| File | Purpose | Key Columns |
|------|---------|-------------|
| `dim_fund.csv` | Fund dimension table | amfi_code, fund_house, scheme_name, category |
| `fact_aum.csv` | AUM by AMC | fund_house, date_id, aum_lakh_crore |
| `fact_sip_industry.csv` | SIP trends | date_id, sip_inflow_crore, active_sip_accounts_crore |
| `fact_category_inflows.csv` | Category flows | date_id, category, net_inflow_crore |
| `fact_industry_folios.csv` | Folio growth | date_id, total_folios_crore |
| `fact_performance.csv` | Performance metrics | amfi_code, sharpe_ratio, alpha, beta |
| `fact_portfolio.csv` | Holdings | amfi_code, stock_name, sector, weight_pct |
| `fact_nav_summary.csv` | NAV summary | amfi_code, latest_nav, records |
| `fact_benchmark_summary.csv` | Benchmark summary | index_name, latest_close |
| `fund_scorecard.csv` | Composite scores | amfi_code, composite_score, tier |
| `sharpe_values.csv` | Sharpe ratios | amfi_code, sharpe_ratio |
| `sortino_values.csv` | Sortino ratios | amfi_code, sortino_ratio |
| `alpha_beta.csv` | Alpha/Beta | amfi_code, alpha_annual, beta |
| `cagr_report.csv` | CAGR values | amfi_code, cagr_1yr, cagr_3yr, cagr_5yr |
| `max_drawdown.csv` | Drawdown | amfi_code, max_drawdown_pct |
| `tracking_error.csv` | Tracking error | amfi_code, tracking_error |
| `transactions_summary.csv` | Transaction agg | transaction_type, state, count |

---

## 2. Data Model & Relationships

### Star Schema

```
dim_fund (1) --> (*) fund_scorecard     ON amfi_code
dim_fund (1) --> (*) fact_performance   ON amfi_code
dim_fund (1) --> (*) fact_portfolio     ON amfi_code
dim_fund (1) --> (*) sharpe_values      ON amfi_code
dim_fund (1) --> (*) sortino_values     ON amfi_code
dim_fund (1) --> (*) alpha_beta         ON amfi_code
dim_fund (1) --> (*) cagr_report        ON amfi_code
dim_fund (1) --> (*) max_drawdown       ON amfi_code
dim_fund (1) --> (*) tracking_error     ON amfi_code
```

### Relationship Setup

1. Go to **Model View**
2. Drag `amfi_code` from `dim_fund` to each fact table
3. Set cardinality: **One to Many**
4. Cross-filter direction: **Single**

---

## 3. DAX Measures

Create a `Measures` table and add these calculated measures:

```dax
// -- KPIs --
Industry AUM = SUM(fact_aum[aum_lakh_crore])

Total Schemes = SUM(fact_aum[num_schemes])

Latest SIP Inflow =
    CALCULATE(
        MAX(fact_sip_industry[sip_inflow_crore]),
        LASTDATE(fact_sip_industry[date_id])
    )

Active SIP Accounts =
    CALCULATE(
        MAX(fact_sip_industry[active_sip_accounts_crore]),
        LASTDATE(fact_sip_industry[date_id])
    )

Total Folios =
    CALCULATE(
        MAX(fact_industry_folios[total_folios_crore]),
        LASTDATE(fact_industry_folios[date_id])
    )

// -- Performance Measures --
Best Sharpe = MAX(sharpe_values[sharpe_ratio])

Best CAGR 3Y = MAX(cagr_report[cagr_3yr]) * 100

Worst Drawdown = MIN(max_drawdown[max_drawdown_pct])

Highest Alpha = MAX(alpha_beta[alpha_annual]) * 100

Average Composite Score = AVERAGE(fund_scorecard[composite_score])

// -- Transaction Measures --
Total Transactions = SUM(transactions_summary[count])

Total Investment Volume = SUM(transactions_summary[total_amount])

SIP Percentage =
    DIVIDE(
        CALCULATE(SUM(transactions_summary[count]),
                  transactions_summary[transaction_type] = "SIP"),
        SUM(transactions_summary[count])
    ) * 100

// -- Portfolio Measures --
Portfolio HHI =
    SUMX(fact_portfolio,
         POWER(fact_portfolio[weight_pct] / 100, 2))

Diversification Score = (1 - [Portfolio HHI]) * 100

Concentration Risk =
    IF([weight_pct] > 10, "High",
       IF([weight_pct] >= 5, "Moderate", "Low"))
```

---

## 4. Theme Configuration

### Custom Theme JSON

Save as `bluestock_theme.json` and import via **View > Themes > Browse**:

```json
{
    "name": "Bluestock Fintech",
    "dataColors": [
        "#0A4D8C", "#00B894", "#E17055", "#6C5CE7",
        "#FDCB6E", "#0984E3", "#D63031", "#00CEC9",
        "#E84393", "#2D3436", "#636E72", "#74B9FF"
    ],
    "background": "#F8FAFC",
    "foreground": "#1F2937",
    "tableAccent": "#0A4D8C",
    "visualStyles": {
        "*": {
            "*": {
                "general": [{"responsive": true}],
                "title": [{
                    "fontFamily": "Segoe UI Semibold",
                    "fontSize": 12,
                    "fontColor": {"solid": {"color": "#1F2937"}}
                }]
            }
        }
    }
}
```

---

## 5. Page Design

### Page 1: Market Overview

| Visual | Type | Data |
|--------|------|------|
| Industry AUM | Card | `[Industry AUM]` |
| Total Folios | Card | `[Total Folios]` |
| Monthly SIP | Card | `[Latest SIP Inflow]` |
| Active SIPs | Card | `[Active SIP Accounts]` |
| AUM Growth | Line Chart | fact_aum: date_id (x), aum_lakh_crore (y), fund_house (legend) |
| SIP Trend | Area Chart | fact_sip_industry: date_id (x), sip_inflow_crore (y) |
| Folio Growth | Line Chart | fact_industry_folios: date_id (x), total_folios_crore (y) |
| Category Heatmap | Matrix | fact_category_inflows: category (rows), date_id (cols), net_inflow_crore (values) |
| Top AMCs | Bar Chart | fact_aum: fund_house (y), aum_lakh_crore (x), Top N = 10 |

### Page 2: Fund Performance

| Visual | Type | Data |
|--------|------|------|
| Best Sharpe | Card | `[Best Sharpe]` |
| Best CAGR | Card | `[Best CAGR 3Y]` |
| Worst DD | Card | `[Worst Drawdown]` |
| Sharpe Ranking | Clustered Bar | sharpe_values: scheme_name (y), sharpe_ratio (x) |
| Sortino Ranking | Clustered Bar | sortino_values: scheme_name (y), sortino_ratio (x) |
| Alpha vs Beta | Scatter | alpha_beta: beta (x), alpha_annual (y) |
| Scorecard | Bar | fund_scorecard: scheme_name (y), composite_score (x) |
| CAGR Heatmap | Matrix | cagr_report: scheme_name (rows), 1Y/3Y/5Y (values), conditional formatting |

### Page 3: Investor Demographics

| Visual | Type | Data |
|--------|------|------|
| Age Distribution | Clustered Bar | transactions_summary: age_group (x), count (y) |
| Gender Split | Donut | transactions_summary: gender (legend), count (values) |
| SIP vs Lumpsum | Donut | transactions_summary: transaction_type (legend), count (values) |
| State Map | Filled Map | transactions_summary: state (location), count (size) |
| T30 vs B30 | Donut | transactions_summary: city_tier (legend), count (values) |
| Income Range | Bar | Use calculated column for income bins |

### Page 4: Portfolio Analytics

| Visual | Type | Data |
|--------|------|------|
| Sector Donut | Donut | fact_portfolio: sector (legend), weight_pct (values) |
| Top Holdings | Bar | fact_portfolio: stock_name (y), weight_pct (x), Top N = 15 |
| Concentration Risk | Table | Conditional formatting on weight_pct |
| Diversification | Bar | Per-fund diversification score |

---

## 6. Filters / Slicers

Add these slicers to every page:
- **AMC Slicer**: dim_fund[fund_house]
- **Category Slicer**: dim_fund[category]
- **Risk Category Slicer**: dim_fund[risk_category]

For Page 1 additionally:
- **Year Slicer**: fact_aum[date_id] (year part)

---

## 7. Publishing

1. Save the `.pbix` file
2. Publish to Power BI Service via **File > Publish**
3. Set up **Scheduled Refresh** if connecting to live SQLite
4. Pin key visuals to a shared **Dashboard**
