import numpy as np
import yfinance as yf

def compute_quality_metrics(symbol: str) -> dict:
    """Universal Buffett/Munger-style quality metrics using Yahoo Finance."""
    t = yf.Ticker(symbol)

    # Income statement (annual)
    income = t.income_stmt
    if income is None or income.empty:
        return {}

    # Cash flow (annual)
    cashflow = t.cashflow
    if cashflow is None or cashflow.empty:
        return {}

    # Balance sheet (annual)
    balance = t.balance_sheet
    if balance is None or balance.empty:
        return {}

    # ROIC (approx using net income and total capital)
    try:
        net_income = float(income.loc["Net Income"].iloc[0])
        total_debt = float(balance.loc["Total Debt"].iloc[0])
        equity = float(balance.loc["Stockholders Equity"].iloc[0])
        roic = net_income / (total_debt + equity) if (total_debt + equity) != 0 else np.nan
    except:
        roic = np.nan

    # Gross margin
    try:
        gross_profit = float(income.loc["Gross Profit"].iloc[0])
        revenue = float(income.loc["Total Revenue"].iloc[0])
        gross_margin = gross_profit / revenue if revenue != 0 else np.nan
    except:
        gross_margin = np.nan

    # Net margin
    try:
        net_margin = net_income / revenue if revenue != 0 else np.nan
    except:
        net_margin = np.nan

    # Revenue CAGR (3 years if available)
    try:
        rev_series = income.loc["Total Revenue"].iloc[:4]
        revenue_cagr = (rev_series.iloc[0] / rev_series.iloc[-1]) ** (1 / (len(rev_series)-1)) - 1
    except:
        revenue_cagr = np.nan

    # FCF CAGR (free cash flow from cashflow)
    try:
        fcf_series = cashflow.loc["Free Cash Flow"].iloc[:4]
        fcf_cagr = (fcf_series.iloc[0] / fcf_series.iloc[-1]) ** (1 / (len(fcf_series)-1)) - 1
    except:
        fcf_cagr = np.nan

    return {
        "roic": roic,
        "gross_margin": gross_margin,
        "net_margin": net_margin,
        "revenue_cagr": revenue_cagr,
        "fcf_cagr": fcf_cagr,
    }


def score_quality(metrics: dict) -> dict:
    """Score fundamental Buffett/Munger-quality characteristics."""
    score = 0

    if metrics.get("roic", 0) and metrics["roic"] > 0.10:
        score += 20

    if metrics.get("gross_margin", 0) and metrics["gross_margin"] > 0.50:
        score += 20

    if metrics.get("net_margin", 0) and metrics["net_margin"] > 0.15:
        score += 20

    if metrics.get("revenue_cagr", 0) and metrics["revenue_cagr"] > 0.10:
        score += 20

    if metrics.get("fcf_cagr", 0) and metrics["fcf_cagr"] > 0.10:
        score += 20

    return {"quality_score": score}
