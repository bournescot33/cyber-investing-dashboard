import numpy as np
from typing import Dict, Any

from .data_providers_yahoo import get_yahoo_financials


def _safe_cagr(start: float, end: float, years: int) -> float:
    """Compute CAGR safely with edge-case protection."""
    if years <= 0:
        return np.nan
    if start <= 0 or end <= 0:
        return np.nan
    return (end / start) ** (1 / years) - 1


def compute_quality_metrics(symbol: str) -> Dict[str, Any]:
    """
    Compute core (universal) quality metrics using Yahoo Finance data.

    Yahoo structure:
      - income: rows = dates, columns = items like "Total Revenue", "Operating Income", "Gross Profit", "Diluted EPS"
      - balance: rows = dates, columns = "Total Liab", "Total Stockholder Equity", etc.
    """
    data = get_yahoo_financials(symbol)

    income = data["income"].sort_index()   # oldest → newest
    balance = data["balance"].sort_index()

    # Make sure required columns exist, else raise a helpful error
    required_income_cols = ["Total Revenue", "Operating Income"]
    for col in required_income_cols:
        if col not in income.columns:
            raise ValueError(f"Missing column '{col}' in Yahoo income statement for {symbol}")

    # --- 1) "ROIC" proxy: use Return on Equity (ROE) 5-year avg ---
    # We approximate ROIC with ROE due to data availability.
    if "Net Income" in income.columns and "Total Stockholder Equity" in balance.columns:
        # Align by index (dates)
        common_index = income.index.intersection(balance.index)
        net_income = income.loc[common_index, "Net Income"]
        equity = balance.loc[common_index, "Total Stockholder Equity"]
        roe_series = net_income / equity.replace(0, np.nan)
        roic_5y_avg = roe_series.tail(5).mean()
    else:
        roic_5y_avg = np.nan

    # --- 2) Operating margin stability (std dev over last 5 years) ---
    op_margin = income["Operating Income"] / income["Total Revenue"].replace(0, np.nan)
    op_margin_5y = op_margin.tail(5)
    op_margin_std = op_margin_5y.std()

    # --- 3) Revenue CAGR (5-year) ---
    rev_series = income["Total Revenue"].dropna()
    rev_6 = rev_series.tail(6)
    if len(rev_6) >= 2:
        rev_cagr_5y = _safe_cagr(rev_6.iloc[0], rev_6.iloc[-1], len(rev_6) - 1)
    else:
        rev_cagr_5y = np.nan

    # --- 4) EPS CAGR (5-year) ---
    eps_col = None
    if "Diluted EPS" in income.columns:
        eps_col = "Diluted EPS"
    elif "Basic EPS" in income.columns:
        eps_col = "Basic EPS"

    if eps_col is not None:
        eps_series = income[eps_col].dropna()
        eps_6 = eps_series.tail(6)
        if len(eps_6) >= 2:
            eps_cagr_5y = _safe_cagr(eps_6.iloc[0], eps_6.iloc[-1], len(eps_6) - 1)
        else:
            eps_cagr_5y = np.nan
    else:
        eps_cagr_5y = np.nan

    # --- 5) Debt-to-equity (latest year) ---
    if "Total Liab" in balance.columns and "Total Stockholder Equity" in balance.columns:
        latest_bal = balance.iloc[-1]
        total_debt = latest_bal["Total Liab"]
        total_equity = latest_bal["Total Stockholder Equity"]
        debt_to_equity = total_debt / total_equity if total_equity not in (0, np.nan) else np.nan
    else:
        debt_to_equity = np.nan

    return {
        "roic_5y_avg": roic_5y_avg,
        "op_margin_std_5y": op_margin_std,
        "rev_cagr_5y": rev_cagr_5y,
        "eps_cagr_5y": eps_cagr_5y,
        "debt_to_equity": debt_to_equity,
    }


def score_quality(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert raw metrics into a 0–100 quality score.
    Same logic as before, just using Yahoo-based inputs.
    """

    score = 0
    max_score = 0

    # --- ROIC/ROE proxy (30 pts) ---
    max_score += 30
    roic = metrics.get("roic_5y_avg")
    if roic is not None and not np.isnan(roic):
        if roic >= 0.20:
            score += 30
        elif roic >= 0.15:
            score += 25
        elif roic >= 0.10:
            score += 15
        elif roic >= 0.05:
            score += 5

    # --- Margin stability (20 pts, lower std = better) ---
    max_score += 20
    op_std = metrics.get("op_margin_std_5y")
    if op_std is not None and not np.isnan(op_std):
        if op_std <= 0.02:
            score += 20
        elif op_std <= 0.05:
            score += 15
        elif op_std <= 0.08:
            score += 8
        elif op_std <= 0.12:
            score += 3

    # --- Revenue CAGR (15 pts) ---
    max_score += 15
    rev_cagr = metrics.get("rev_cagr_5y")
    if rev_cagr is not None and not np.isnan(rev_cagr):
        if rev_cagr >= 0.15:
            score += 15
        elif rev_cagr >= 0.10:
            score += 12
        elif rev_cagr >= 0.05:
            score += 7
        elif rev_cagr >= 0.02:
            score += 3

    # --- EPS CAGR (15 pts) ---
    max_score += 15
    eps_cagr = metrics.get("eps_cagr_5y")
    if eps_cagr is not None and not np.isnan(eps_cagr):
        if eps_cagr >= 0.15:
            score += 15
        elif eps_cagr >= 0.10:
            score += 12
        elif eps_cagr >= 0.05:
            score += 7
        elif eps_cagr >= 0.02:
            score += 3

    # --- Debt-to-equity (20 pts, lower = better) ---
    max_score += 20
    dte = metrics.get("debt_to_equity")
    if dte is not None and not np.isnan(dte):
        if dte <= 0.5:
            score += 20
        elif dte <= 1.0:
            score += 15
        elif dte <= 1.5:
            score += 8
        elif dte <= 2.0:
            score += 3

    quality_score = round(100 * score / max_score) if max_score > 0 else np.nan

    return {
        **metrics,
        "quality_score": quality_score,
    }
