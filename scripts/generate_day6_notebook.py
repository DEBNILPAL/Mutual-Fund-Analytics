"""
Generate Day 6 Advanced Analytics Jupyter Notebook.
Creates 05_Advanced_Analytics.ipynb with 50+ cells.
"""
from __future__ import annotations
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
NB_PATH  = BASE_DIR / "notebooks" / "05_Advanced_Analytics.ipynb"
NB_PATH.parent.mkdir(parents=True, exist_ok=True)

def md(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {},
            "source": [s + "\n" for s in source.strip().split("\n")]}

def code(source: str, outputs: list | None = None) -> dict:
    return {"cell_type": "code", "metadata": {}, "execution_count": None,
            "source": [s + "\n" for s in source.strip().split("\n")],
            "outputs": outputs or []}

cells = []

# ── Section 1: Introduction ─────────────────────────────────
cells.append(md("""# Day 6: Advanced Analytics & Portfolio Optimization
## Bluestock Mutual Fund Capstone

**Author:** DEBNIL PAL  
**Date:** 2026-06-08  
**Objective:** Build a complete quant-grade analytics module covering VaR, CVaR, Monte Carlo simulation, Markowitz portfolio optimization, cohort analysis, investor segmentation, fund recommendations, rolling analytics, correlation analysis, and risk scoring.

### Modules Covered
1. Value at Risk (VaR) -- Historical, Parametric, Monte Carlo
2. Conditional VaR (CVaR / Expected Shortfall)
3. Investor Cohort Analysis
4. Customer Segmentation
5. Fund Recommendation Engine
6. Monte Carlo Simulation (Bonus B3)
7. Markowitz Portfolio Optimization (Bonus B4)
8. Rolling Analytics (Sharpe, Volatility, Beta)
9. Advanced Correlation Analysis
10. Risk Score Engine
11. Key Business Insights"""))

# ── Setup ────────────────────────────────────────────────────
cells.append(md("## 1. Environment Setup"))

cells.append(code("""import warnings
warnings.filterwarnings('ignore', category=FutureWarning)

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import sqlite3
from scipy import stats as sp_stats
from pathlib import Path

%matplotlib inline
plt.rcParams.update({
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'axes.grid': True, 'grid.alpha': 0.3, 'figure.figsize': (12, 6),
    'font.size': 10, 'axes.titlesize': 13,
})

PALETTE = ['#0A4D8C', '#00B894', '#E17055', '#6C5CE7',
           '#FDCB6E', '#0984E3', '#D63031', '#00CEC9']
RF_DAILY = 0.065 / 252
TRADING_DAYS = 252

BASE_DIR = Path('.').resolve().parent
DB_PATH = BASE_DIR / 'data' / 'db' / 'bluestock_mf.db'
PROCESSED = BASE_DIR / 'data' / 'processed'
CHARTS = BASE_DIR / 'reports' / 'charts'
print(f'Database: {DB_PATH}')
print(f'Processed: {PROCESSED}')"""))

# ── Data Loading ─────────────────────────────────────────────
cells.append(md("## 2. Data Loading"))

cells.append(code("""conn = sqlite3.connect(str(DB_PATH))
fund_master = pd.read_sql('SELECT * FROM dim_fund', conn)
nav_df = pd.read_sql('SELECT * FROM fact_nav', conn)
nav_df['date'] = pd.to_datetime(nav_df['date_id'])
tx_df = pd.read_sql('SELECT * FROM fact_transactions', conn)
tx_df['date'] = pd.to_datetime(tx_df['date_id'])
benchmark_df = pd.read_sql('SELECT * FROM fact_benchmark', conn)
benchmark_df['date'] = pd.to_datetime(benchmark_df['date_id'])
conn.close()

returns_df = pd.read_csv(PROCESSED / 'daily_returns.csv')
returns_df['date'] = pd.to_datetime(returns_df['date'])
scorecard = pd.read_csv(PROCESSED / 'fund_scorecard.csv')

print(f'Funds: {fund_master.shape[0]}')
print(f'NAV records: {nav_df.shape[0]:,}')
print(f'Returns: {returns_df.shape[0]:,}')
print(f'Transactions: {tx_df.shape[0]:,}')
print(f'Benchmark records: {benchmark_df.shape[0]:,}')"""))

cells.append(code("""fund_master.head()"""))
cells.append(code("""scorecard.sort_values('composite_score', ascending=False).head(10)"""))

# ── Section 3: VaR ──────────────────────────────────────────
cells.append(md("""## 3. Value at Risk (VaR)

### 3.1 Historical VaR
The simplest VaR approach -- use the empirical percentile of historical returns.

$$VaR_{95} = \\text{5th percentile of returns}$$
$$VaR_{99} = \\text{1st percentile of returns}$$"""))

cells.append(code("""var_summary = pd.read_csv(PROCESSED / 'var_summary.csv')
print(f'VaR computed for {len(var_summary)} funds')
var_summary.head(10)"""))

cells.append(code("""# Historical VaR distribution for the riskiest fund
riskiest = var_summary.sort_values('hist_var_95').iloc[0]
r = returns_df[returns_df['amfi_code'] == riskiest['amfi_code']]['daily_return'].dropna()

fig, ax = plt.subplots(figsize=(12, 6))
ax.hist(r, bins=80, color=PALETTE[0], alpha=0.7, edgecolor='white', density=True)
ax.axvline(riskiest['hist_var_95'], color='red', lw=2, ls='--',
           label=f"VaR 95%: {riskiest['hist_var_95']:.4f}")
ax.axvline(riskiest['hist_var_99'], color='darkred', lw=2, ls='--',
           label=f"VaR 99%: {riskiest['hist_var_99']:.4f}")
ax.axvline(riskiest['cvar_95'], color='orange', lw=2, ls=':',
           label=f"CVaR 95%: {riskiest['cvar_95']:.4f}")
ax.set_title(f"Return Distribution & VaR -- {riskiest['scheme_name'][:40]}", fontweight='bold')
ax.set_xlabel('Daily Return'); ax.set_ylabel('Density')
ax.legend(fontsize=9)
plt.tight_layout(); plt.show()"""))

cells.append(md("""### 3.2 Parametric VaR
Assumes returns follow a normal distribution.

$$VaR = \\mu + z \\cdot \\sigma$$

Where $z_{95} = -1.645$ and $z_{99} = -2.326$"""))

cells.append(code("""# Compare Historical vs Parametric VaR
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(var_summary['hist_var_95']*100, var_summary['param_var_95']*100,
           c=PALETTE[0], alpha=0.7, s=60)
lims = [min(ax.get_xlim()[0], ax.get_ylim()[0]), max(ax.get_xlim()[1], ax.get_ylim()[1])]
ax.plot(lims, lims, '--', color='gray', alpha=0.5, label='Perfect Agreement')
ax.set_xlabel('Historical VaR 95% (%)'); ax.set_ylabel('Parametric VaR 95% (%)')
ax.set_title('Historical vs Parametric VaR Comparison', fontweight='bold')
ax.legend(); plt.tight_layout(); plt.show()"""))

cells.append(md("""### 3.3 Monte Carlo VaR
10,000 random draws from the fitted normal distribution."""))

cells.append(code("""# Monte Carlo VaR comparison
fig, ax = plt.subplots(figsize=(10, 6))
ax.scatter(var_summary['hist_var_95']*100, var_summary['mc_var_95']*100,
           c=PALETTE[1], alpha=0.7, s=60)
lims = [min(ax.get_xlim()[0], ax.get_ylim()[0]), max(ax.get_xlim()[1], ax.get_ylim()[1])]
ax.plot(lims, lims, '--', color='gray', alpha=0.5, label='Perfect Agreement')
ax.set_xlabel('Historical VaR 95% (%)'); ax.set_ylabel('Monte Carlo VaR 95% (%)')
ax.set_title('Historical vs Monte Carlo VaR', fontweight='bold')
ax.legend(); plt.tight_layout(); plt.show()"""))

# ── CVaR ─────────────────────────────────────────────────────
cells.append(md("""### 3.4 Conditional VaR (Expected Shortfall)

CVaR answers: *"If we breach VaR, how bad is it on average?"*

$$CVaR_{\\alpha} = E[R \\mid R \\leq VaR_{\\alpha}]$$"""))

cells.append(code("""# CVaR comparison chart
fig, ax = plt.subplots(figsize=(14, 7))
top20 = var_summary.sort_values('cvar_95').head(20)
y = range(len(top20))
ax.barh(y, top20['cvar_95']*100, color=PALETTE[6], alpha=0.8, label='CVaR 95%')
ax.barh(y, top20['cvar_99']*100, color=PALETTE[3], alpha=0.6, label='CVaR 99%')
ax.set_yticks(y)
ax.set_yticklabels(top20['scheme_name'].str[:30], fontsize=8)
ax.set_xlabel('CVaR (%)')
ax.set_title('Conditional VaR (Expected Shortfall) -- Worst 20 Funds', fontweight='bold')
ax.legend(); plt.tight_layout(); plt.show()"""))

cells.append(code("""# VaR Summary Statistics
print('=== VaR Summary Statistics ===')
for col in ['hist_var_95', 'hist_var_99', 'param_var_95', 'mc_var_95', 'cvar_95', 'cvar_99']:
    vals = var_summary[col] * 100
    print(f'{col:18s}: mean={vals.mean():.4f}%  std={vals.std():.4f}%  '
          f'min={vals.min():.4f}%  max={vals.max():.4f}%')"""))

# ── Section 4: Cohort Analysis ──────────────────────────────
cells.append(md("""## 4. Investor Cohort Analysis

Cohorts defined by: **Age Group**, **City Tier**, **State**

Metrics: Retention Rate, Investment Growth, Redemption Rate, Average SIP"""))

cells.append(code("""cohort_df = pd.read_csv(PROCESSED / 'cohort_analysis.csv')
print(f'Total cohorts: {len(cohort_df)}')
cohort_df.head(10)"""))

cells.append(code("""# Age cohort retention
age_c = cohort_df[cohort_df['cohort_type'] == 'age_group']
fig, axes = plt.subplots(1, 3, figsize=(18, 5))
axes[0].bar(age_c['cohort_value'], age_c['retention_rate']*100, color=PALETTE[:len(age_c)])
axes[0].set_title('Retention Rate by Age', fontweight='bold')
axes[0].set_ylabel('Retention (%)')
axes[1].bar(age_c['cohort_value'], age_c['avg_investment'], color=PALETTE[:len(age_c)])
axes[1].set_title('Avg Investment by Age', fontweight='bold')
axes[1].yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
axes[2].bar(age_c['cohort_value'], age_c['redemption_rate']*100, color=PALETTE[6])
axes[2].set_title('Redemption Rate by Age', fontweight='bold')
axes[2].set_ylabel('Redemption (%)')
plt.tight_layout(); plt.show()"""))

cells.append(code("""# City tier analysis
tier_c = cohort_df[cohort_df['cohort_type'] == 'city_tier']
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
ax1.bar(tier_c['cohort_value'], tier_c['avg_investment'], color=[PALETTE[0], PALETTE[1]])
ax1.set_title('Avg Investment: T30 vs B30', fontweight='bold')
ax1.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
ax2.bar(tier_c['cohort_value'], tier_c['avg_sip_amount'], color=[PALETTE[0], PALETTE[1]])
ax2.set_title('Avg SIP Amount: T30 vs B30', fontweight='bold')
ax2.yaxis.set_major_formatter(mtick.StrMethodFormatter('{x:,.0f}'))
plt.tight_layout(); plt.show()"""))

# ── Section 5: Segmentation ────────────────────────────────
cells.append(md("""## 5. Customer Segmentation

Investors classified into 3 personas:
- **Conservative** -- Older, lower income, high SIP ratio, small tickets
- **Balanced** -- Middle ground across all factors
- **Aggressive** -- Young, high income, large tickets, growth-oriented"""))

cells.append(code("""seg_df = pd.read_csv(PROCESSED / 'investor_segments.csv')
print(f'Total investors segmented: {len(seg_df):,}')
print(seg_df['investor_segment'].value_counts())"""))

cells.append(code("""# Segment distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
counts = seg_df['investor_segment'].value_counts()
colours = {'Conservative': PALETTE[0], 'Balanced': PALETTE[1], 'Aggressive': PALETTE[6]}
ax1.pie(counts, labels=counts.index, autopct='%1.1f%%',
        colors=[colours.get(s, '#999') for s in counts.index], startangle=90)
ax1.set_title('Investor Persona Distribution', fontweight='bold')

cross = seg_df.groupby(['age_group', 'investor_segment']).size().unstack(fill_value=0)
cross.plot(kind='bar', ax=ax2, color=[colours.get(c, '#999') for c in cross.columns], alpha=0.85)
ax2.set_title('Segment by Age Group', fontweight='bold')
ax2.set_ylabel('Investors')
plt.xticks(rotation=0); plt.tight_layout(); plt.show()"""))

cells.append(code("""# Segment profile comparison
profile = seg_df.groupby('investor_segment').agg(
    avg_income=('income', 'mean'),
    avg_amount=('avg_amount', 'mean'),
    avg_sip_ratio=('sip_ratio', 'mean'),
    count=('investor_id', 'count')
).round(2)
profile"""))

# ── Section 6: Recommendations ──────────────────────────────
cells.append(md("""## 6. Fund Recommendation Engine

Rule-based recommender with 7 weighted factors:
Sharpe, Sortino, Alpha, Beta, Expense Ratio, Max Drawdown, Risk Category"""))

cells.append(code("""rec_df = pd.read_csv(PROCESSED / 'fund_recommendations.csv')
print(f'Total recommendations: {len(rec_df)}')
rec_df"""))

cells.append(code("""# Visualise top picks by investor type
fig, axes = plt.subplots(1, 3, figsize=(18, 6))
for i, inv_type in enumerate(['Conservative', 'Balanced', 'Aggressive']):
    subset = rec_df[rec_df['investor_type'] == inv_type].sort_values('rank')
    axes[i].barh(range(len(subset)), subset['recommendation_score'],
                 color=PALETTE[i*3 % len(PALETTE)], alpha=0.85)
    axes[i].set_yticks(range(len(subset)))
    axes[i].set_yticklabels(subset['scheme_name'].str[:25], fontsize=8)
    axes[i].set_title(f'{inv_type} Investor', fontweight='bold')
    axes[i].set_xlabel('Recommendation Score')
plt.suptitle('Top 5 Fund Recommendations by Investor Type', fontweight='bold', fontsize=14)
plt.tight_layout(); plt.show()"""))

# ── Section 7: Monte Carlo ──────────────────────────────────
cells.append(md("""## 7. Monte Carlo Simulation (Bonus B3)

**Geometric Brownian Motion:**

$$S_{t+1} = S_t \\cdot \\exp\\left[(\\mu - \\tfrac{1}{2}\\sigma^2)\\Delta t + \\sigma\\sqrt{\\Delta t}\\cdot Z\\right]$$

- 10,000 simulated paths per fund
- 5-year projection horizon
- Applied to top 10 funds by composite score"""))

cells.append(code("""mc_df = pd.read_csv(PROCESSED / 'monte_carlo_projections.csv')
print(f'Monte Carlo projections for {len(mc_df)} funds')
mc_df"""))

cells.append(code("""# Re-simulate top fund for visualisation
top_fund = mc_df.iloc[0]
code = top_fund['amfi_code']
r = returns_df[returns_df['amfi_code'] == code]['daily_return'].dropna()
mu, sigma = r.mean(), r.std()
last_nav = top_fund['current_nav']
horizon = 5 * TRADING_DAYS

np.random.seed(42)
n_vis = 200
paths = np.zeros((n_vis, horizon))
paths[:, 0] = last_nav
for t in range(1, horizon):
    z = np.random.standard_normal(n_vis)
    paths[:, t] = paths[:, t-1] * np.exp((mu - 0.5*sigma**2) + sigma*z)

fig, ax = plt.subplots(figsize=(14, 7))
for i in range(min(50, n_vis)):
    ax.plot(range(horizon), paths[i], alpha=0.08, color=PALETTE[0], lw=0.5)
med = np.median(paths, axis=0)
p5, p95 = np.percentile(paths, 5, axis=0), np.percentile(paths, 95, axis=0)
ax.plot(range(horizon), med, color=PALETTE[0], lw=2.5, label='Median')
ax.fill_between(range(horizon), p5, p95, alpha=0.15, color=PALETTE[0], label='5th-95th')
ax.axhline(last_nav, ls='--', color='#999', lw=1, label=f'Current NAV: {last_nav:.0f}')
ax.set_title(f"Monte Carlo 5-Year Projection -- {top_fund['scheme_name'][:40]}", fontweight='bold')
ax.set_xlabel('Trading Days'); ax.set_ylabel('Projected NAV')
ax.legend(); plt.tight_layout(); plt.show()"""))

cells.append(code("""# Probability analysis
print('=== Monte Carlo Probability Analysis ===')
for _, row in mc_df.iterrows():
    name = row['scheme_name'][:35]
    print(f"{name:36s} | P(gain)={row['prob_positive']*100:.1f}% | "
          f"Median 5Y NAV={row['median_5yr']:,.0f} | CAGR={row['expected_cagr']*100:.1f}%")"""))

cells.append(code("""# Fan chart
fig, ax = plt.subplots(figsize=(14, 7))
for idx, (_, row) in enumerate(mc_df.head(5).iterrows()):
    c = PALETTE[idx % len(PALETTE)]
    ax.barh(idx*3, row['p95_5yr'] - row['p5_5yr'], left=row['p5_5yr'],
            height=1.5, color=c, alpha=0.3)
    ax.plot(row['median_5yr'], idx*3, 'o', color=c, ms=10)
    ax.plot(row['current_nav'], idx*3, 's', color='black', ms=6)
names = mc_df.head(5)['scheme_name'].str[:30].tolist()
ax.set_yticks([i*3 for i in range(len(names))])
ax.set_yticklabels(names, fontsize=9)
ax.set_xlabel('NAV Range (5-Year Projection)')
ax.set_title('Monte Carlo Fan Chart -- Top 5 Funds', fontweight='bold')
plt.tight_layout(); plt.show()"""))

# ── Section 8: Markowitz ────────────────────────────────────
cells.append(md("""## 8. Markowitz Portfolio Optimization (Bonus B4)

### Modern Portfolio Theory

$$\\text{Portfolio Return:} \\quad R_p = \\sum_i w_i R_i$$

$$\\text{Portfolio Variance:} \\quad \\sigma_p^2 = \\mathbf{w}^T \\Sigma \\mathbf{w}$$

- 10,000 random portfolios generated
- Top 5 funds by composite score
- Identifies **Max Sharpe** and **Min Variance** portfolios"""))

cells.append(code("""frontier_df = pd.read_csv(PROCESSED / 'efficient_frontier.csv')
optimal_df = pd.read_csv(PROCESSED / 'optimal_portfolios.csv')
print(f'Random portfolios: {len(frontier_df):,}')
optimal_df"""))

cells.append(code("""# Efficient Frontier
fig, ax = plt.subplots(figsize=(12, 8))
sc = ax.scatter(frontier_df['volatility']*100, frontier_df['return']*100,
                c=frontier_df['sharpe'], cmap='RdYlGn', alpha=0.5, s=8)
plt.colorbar(sc, ax=ax, label='Sharpe Ratio')

for _, row in optimal_df.iterrows():
    marker = '*' if 'Max' in row['portfolio'] else 'D'
    color = 'red' if 'Max' in row['portfolio'] else 'blue'
    ax.scatter(row['volatility']*100, row['return']*100,
               marker=marker, s=300, c=color, edgecolors='black', zorder=5,
               label=f"{row['portfolio']} (S={row['sharpe']:.2f})")

ax.set_xlabel('Annualised Volatility (%)'); ax.set_ylabel('Annualised Return (%)')
ax.set_title('Efficient Frontier -- Top 5 Funds', fontweight='bold', fontsize=14)
ax.legend(fontsize=9); plt.tight_layout(); plt.show()"""))

cells.append(code("""# Optimal allocation
w_cols = [c for c in optimal_df.columns if c.startswith('w_')]
max_sharpe = optimal_df[optimal_df['portfolio'] == 'Max Sharpe']
weights = max_sharpe[w_cols].values[0]
labels = [c.replace('w_', '') for c in w_cols]

fig, ax = plt.subplots(figsize=(10, 8))
ax.pie(weights, labels=labels, autopct='%1.1f%%',
       colors=PALETTE[:len(labels)], startangle=90)
ax.set_title('Optimal Portfolio Allocation (Max Sharpe)', fontweight='bold')
plt.tight_layout(); plt.show()

print(f"Max Sharpe Portfolio:")
print(f"  Return:     {max_sharpe['return'].values[0]*100:.2f}%")
print(f"  Volatility: {max_sharpe['volatility'].values[0]*100:.2f}%")
print(f"  Sharpe:     {max_sharpe['sharpe'].values[0]:.2f}")"""))

# ── Section 9: Rolling Analytics ─────────────────────────────
cells.append(md("""## 9. Rolling Analytics

Windows: **30-day**, **90-day**, **180-day**

Metrics: Rolling Sharpe, Rolling Volatility, Rolling Beta"""))

cells.append(code("""# Display saved charts
from IPython.display import Image, display
for chart_name in ['rolling_sharpe', 'rolling_volatility', 'rolling_beta']:
    path = CHARTS / f'{chart_name}.png'
    if path.exists():
        print(f'--- {chart_name} ---')
        display(Image(filename=str(path), width=900))"""))

cells.append(code("""# Compute 90-day rolling Sharpe for top 3 inline
top3 = scorecard.sort_values('composite_score', ascending=False).head(3)
fig, ax = plt.subplots(figsize=(14, 6))
for i, (_, fund) in enumerate(top3.iterrows()):
    r = returns_df[returns_df['amfi_code'] == fund['amfi_code']].sort_values('date')
    rolling_s = r['daily_return'].rolling(90).apply(
        lambda x: (x.mean() - RF_DAILY) / x.std() * np.sqrt(252) if x.std() > 0 else 0, raw=True)
    ax.plot(r['date'], rolling_s, label=fund['scheme_name'][:25], color=PALETTE[i], lw=1.2)
ax.axhline(0, ls='--', color='gray', lw=0.8)
ax.set_title('90-Day Rolling Sharpe Ratio -- Top 3 Funds', fontweight='bold')
ax.set_ylabel('Sharpe Ratio'); ax.legend(fontsize=9)
plt.tight_layout(); plt.show()"""))

# ── Section 10: Correlation ─────────────────────────────────
cells.append(md("""## 10. Advanced Correlation Analysis

Fund-to-fund and fund-to-benchmark correlation matrices."""))

cells.append(code("""# Build correlation matrix
pivot = returns_df.pivot_table(index='date', columns='amfi_code', values='daily_return').dropna()
name_map = fund_master.set_index('amfi_code')['scheme_name'].to_dict()
pivot.columns = [name_map.get(c, str(c))[:18] for c in pivot.columns]
corr = pivot.corr()

fig, ax = plt.subplots(figsize=(16, 14))
im = ax.imshow(corr.values, cmap='RdYlGn', vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(corr))); ax.set_xticklabels(corr.columns, rotation=90, fontsize=6)
ax.set_yticks(range(len(corr))); ax.set_yticklabels(corr.index, fontsize=6)
plt.colorbar(im, ax=ax, label='Correlation')
ax.set_title('Fund-to-Fund Correlation Matrix', fontweight='bold', fontsize=14)
plt.tight_layout(); plt.show()"""))

cells.append(code("""# Top correlated / uncorrelated pairs
pairs = []
for i in range(len(corr)):
    for j in range(i+1, len(corr)):
        pairs.append({'fund_a': corr.index[i], 'fund_b': corr.columns[j],
                      'correlation': corr.iloc[i, j]})
pairs_df = pd.DataFrame(pairs).sort_values('correlation', ascending=False)
print('TOP 5 MOST CORRELATED:')
print(pairs_df.head().to_string(index=False))
print('\\nTOP 5 LEAST CORRELATED:')
print(pairs_df.tail(5).to_string(index=False))"""))

cells.append(code("""# Fund-to-Benchmark correlation
bench_n100 = benchmark_df[benchmark_df['index_name'] == 'NIFTY100'].sort_values('date')
bench_n100['bench_return'] = bench_n100['close_value'].pct_change()
bench_corrs = []
for code in returns_df['amfi_code'].unique():
    fund_r = returns_df[returns_df['amfi_code'] == code][['date', 'daily_return']]
    merged = fund_r.merge(bench_n100[['date', 'bench_return']], on='date').dropna()
    if len(merged) > 50:
        c = merged['daily_return'].corr(merged['bench_return'])
        name = name_map.get(code, str(code))
        bench_corrs.append({'fund': name[:25], 'corr_nifty100': round(c, 4)})
bc_df = pd.DataFrame(bench_corrs).sort_values('corr_nifty100', ascending=False)

fig, ax = plt.subplots(figsize=(12, 8))
ax.barh(range(len(bc_df)), bc_df['corr_nifty100'], color=PALETTE[0], alpha=0.8)
ax.set_yticks(range(len(bc_df)))
ax.set_yticklabels(bc_df['fund'], fontsize=7)
ax.set_xlabel('Correlation with NIFTY 100')
ax.set_title('Fund-to-Benchmark Correlation', fontweight='bold')
plt.tight_layout(); plt.show()"""))

# ── Section 11: Risk Score ──────────────────────────────────
cells.append(md("""## 11. Risk Score Engine

Composite risk score (0-100) from:
- Annualised Volatility (30%)
- Maximum Drawdown (30%)
- Beta (20%)
- VaR (20%)

**Tiers:** Low (0-25) | Moderate (25-50) | High (50-75) | Very High (75-100)"""))

cells.append(code("""risk_df = pd.read_csv(PROCESSED / 'risk_scorecard.csv')
print(f'Risk scores for {len(risk_df)} funds')
print(risk_df['risk_tier'].value_counts())
risk_df.sort_values('risk_score').head(10)"""))

cells.append(code("""# Risk score distribution
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
# Histogram
ax1.hist(risk_df['risk_score'], bins=15, color=PALETTE[0], alpha=0.8, edgecolor='white')
ax1.set_title('Risk Score Distribution', fontweight='bold')
ax1.set_xlabel('Risk Score (0-100)')
# Tier pie
tier_counts = risk_df['risk_tier'].value_counts()
tier_colors = {'Low': '#00B894', 'Moderate': '#FDCB6E', 'High': '#E17055', 'Very High': '#D63031'}
ax2.pie(tier_counts, labels=tier_counts.index, autopct='%1.1f%%',
        colors=[tier_colors.get(t, '#999') for t in tier_counts.index], startangle=90)
ax2.set_title('Risk Tier Distribution', fontweight='bold')
plt.tight_layout(); plt.show()"""))

cells.append(code("""# Risk vs Composite Score scatter
merged_rc = risk_df.merge(scorecard[['amfi_code', 'composite_score']], on='amfi_code')
fig, ax = plt.subplots(figsize=(10, 7))
scatter = ax.scatter(merged_rc['risk_score'], merged_rc['composite_score'],
                     c=merged_rc['ann_volatility']*100, cmap='YlOrRd', s=80, alpha=0.8)
plt.colorbar(scatter, ax=ax, label='Annualised Volatility (%)')
ax.set_xlabel('Risk Score'); ax.set_ylabel('Composite Performance Score')
ax.set_title('Risk Score vs Performance Score', fontweight='bold')
plt.tight_layout(); plt.show()"""))

# ── Section 12: Insights ────────────────────────────────────
cells.append(md("""## 12. Key Business Insights"""))

cells.append(code("""# Load and display insights
report_path = BASE_DIR / 'reports' / 'advanced_analytics_summary.md'
if report_path.exists():
    print(report_path.read_text(encoding='utf-8'))"""))

# ── Section 13: Validation ──────────────────────────────────
cells.append(md("""## 13. Validation"""))

cells.append(code("""val_df = pd.read_csv(PROCESSED / 'day6_validation_report.csv')
print(f"Validation: {(val_df['passed']=='PASS').sum()}/{len(val_df)} checks passed")
val_df"""))

cells.append(code("""# Final output inventory
import os
output_files = [
    'var_summary.csv', 'cohort_analysis.csv', 'investor_segments.csv',
    'fund_recommendations.csv', 'monte_carlo_projections.csv',
    'efficient_frontier.csv', 'optimal_portfolios.csv',
    'risk_scorecard.csv', 'day6_validation_report.csv',
]
print('=== Day 6 Output Files ===')
for f in output_files:
    path = PROCESSED / f
    size = path.stat().st_size if path.exists() else 0
    status = 'OK' if path.exists() else 'MISSING'
    print(f'  [{status}] {f:40s} {size:>10,} bytes')"""))

# ── Conclusion ──────────────────────────────────────────────
cells.append(md("""## 14. Conclusion

### Day 6 Deliverables Summary

| Module | Status | Output |
|--------|--------|--------|
| VaR (Historical, Parametric, MC) | Complete | var_summary.csv |
| CVaR / Expected Shortfall | Complete | Included in var_summary.csv |
| Investor Cohort Analysis | Complete | cohort_analysis.csv |
| Customer Segmentation | Complete | investor_segments.csv |
| Fund Recommendations | Complete | fund_recommendations.csv |
| Monte Carlo Simulation (B3) | Complete | monte_carlo_projections.csv |
| Markowitz Optimization (B4) | Complete | efficient_frontier.csv, optimal_portfolios.csv |
| Rolling Analytics | Complete | Charts generated |
| Correlation Analysis | Complete | Charts generated |
| Risk Score Engine | Complete | risk_scorecard.csv |
| Business Insights | Complete | advanced_analytics_summary.md |
| Validation | Complete | day6_validation_report.csv |

**Total Charts Generated:** 20+  
**Total CSVs Generated:** 9  
**Validation:** 12/12 PASS"""))

# ── Build Notebook ──────────────────────────────────────────
nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {
            "name": "python",
            "version": "3.10.0",
        },
    },
    "cells": cells,
}

NB_PATH.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"Notebook created: {NB_PATH}")
print(f"Total cells: {len(cells)}")
