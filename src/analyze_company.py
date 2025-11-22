import numpy as np
import yfinance as yf

from .quality import compute_quality_metrics, score_quality
from .quality_cyber import compute_cyber_metrics, score_cyber_styles
from .data_providers_yahoo import get_yahoo_financials


def _fmt(x, pct=False, decimals=2):
    """Human-friendly formatting."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "N/A"
    if pct:
        return f"{x*100:.{decimals}f}%"
    return f"{x:.{decimals}f}"


def get_basic_valuation(symbol: str):
    """
    Fetch simple valuation metrics using yfinance.
    Returns: dict with pe, peg, ps, pb, fcf_yield (if available)
    """
    t = yf.Ticker(symbol)
    info = t.info or {}

    pe = info.get("trailingPE")
    peg = info.get("pegRatio")
    ps = info.get("priceToSalesTrailing12Months")
    pb = info.get("priceToBook")
    mcap = info.get("marketCap")

    # Free Cash Flow (from cashflow statement)
    try:
        cf = t.cashflow
        if cf is not None and "Free Cash Flow" in cf.index:
            fcf = cf.loc["Free Cash Flow"].dropna().iloc[0]
            if mcap:
                fcf_yield = fcf / mcap
            else:
                fcf_yield = np.nan
        else:
            fcf_yield = np.nan
    except Exception:
        fcf_yield = np.nan

    return {
        "pe": pe,
        "peg": peg,
        "ps": ps,
        "pb": pb,
        "fcf_yield": fcf_yield,
    }


def analyze_company(symbol: str) -> str:
    """
    Unified analyzer that combines:
      - Universal quality metrics
      - Cyber-specific metrics
      - Valuation metrics
    and returns a clean human-readable report.
    """
    # -------------------------------
    # UNIVERSAL (Buffett/Munger Style)
    # -------------------------------
    base_metrics = compute_quality_metrics(symbol)
    base_score = score_quality(base_metrics)

    # -------------------------------
    # CYBER (Growth/Profitability/Balanced)
    # -------------------------------
    cyber_raw = compute_cyber_metrics(symbol)
    cyber_scores = score_cyber_styles(cyber_raw)

    # -------------------------------
    # VALUATION
    # -------------------------------
    val = get_basic_valuation(symbol)

    # -------------------------------
    # BUILD REPORT STRING
    # -------------------------------
    lines = []
    lines.append(f"==============================")
    lines.append(f"   ANALYSIS REPORT: {symbol}")
    lines.append(f"==============================\n")

    # UNIVERSAL
    lines.append("UNIVERSAL QUALITY SCORE (Buffett/Munger Style)")
    lines.append("----------------------------------------------")
    lines.append(f"Quality Score:          {_fmt(base_score.get('quality_score'), pct=False, decimals=0)}")

    # Map/derive metrics from the quality modules
    roic = base_metrics.get("roic_5y_avg")
    revenue_cagr = base_metrics.get("rev_cagr_5y") or base_metrics.get("revenue_cagr")

    # Try to compute net margin and FCF growth from Yahoo financials
    try:
        yahoo = get_yahoo_financials(symbol)
        income_df = yahoo.get("income")
        cashflow_df = yahoo.get("cashflow")

        net_margin = np.nan
        if (
            isinstance(income_df, type(income_df)) and
            income_df is not None and
            "Net Income" in income_df.columns and
            "Total Revenue" in income_df.columns
        ):
            ni = income_df["Net Income"].dropna().tail(1)
            rev = income_df["Total Revenue"].dropna().tail(1)
            if len(ni) == 1 and len(rev) == 1 and rev.iloc[0] != 0:
                net_margin = ni.iloc[0] / rev.iloc[0]

        # FCF CAGR (5-year proxy) from cashflow 'Free Cash Flow' if available
        fcf_cagr = np.nan
        if (
            isinstance(cashflow_df, type(cashflow_df)) and
            cashflow_df is not None and
            "Free Cash Flow" in cashflow_df.columns
        ):
            fcf_series = cashflow_df["Free Cash Flow"].dropna()
            fcf_6 = fcf_series.tail(6)
            if len(fcf_6) >= 2 and fcf_6.iloc[0] > 0 and fcf_6.iloc[-1] > 0:
                years = len(fcf_6) - 1
                fcf_cagr = (fcf_6.iloc[-1] / fcf_6.iloc[0]) ** (1 / years) - 1
    except Exception:
        net_margin = np.nan
        fcf_cagr = np.nan

    lines.append(f"ROIC:                    {_fmt(roic, pct=True)}")
    lines.append(f"Gross Margin:            {_fmt(cyber_raw.get('gross_margin_avg'), pct=True)}")
    lines.append(f"Net Margin:              {_fmt(net_margin, pct=True)}")
    lines.append(f"Revenue CAGR:            {_fmt(revenue_cagr, pct=True)}")
    lines.append(f"FCF Growth:              {_fmt(fcf_cagr, pct=True)}\n")

    # CYBER-SPECIFIC
    lines.append("CYBER BUSINESS QUALITY")
    lines.append("----------------------------------------------")
    lines.append(f"Growth Score:            {_fmt(cyber_scores.get('growth_score'), pct=False, decimals=0)}")
    lines.append(f"Profitability Score:     {_fmt(cyber_scores.get('profitability_score'), pct=False, decimals=0)}")
    lines.append(f"Balanced Score:          {_fmt(cyber_scores.get('balanced_score'), pct=False, decimals=0)}")
    lines.append("")
    lines.append(f"ARR Growth (CAGR proxy): {_fmt(cyber_raw.get('arr_growth'), pct=True)}")
    lines.append(f"Gross Margin Avg:        {_fmt(cyber_raw.get('gross_margin_avg'), pct=True)}")
    lines.append(f"Gross Margin Trend:      {_fmt(cyber_raw.get('gross_margin_trend'), pct=True)}")
    lines.append(f"FCF Margin:              {_fmt(cyber_raw.get('fcf_margin'), pct=True)}")
    lines.append(f"Rule of 40:              {_fmt(cyber_raw.get('rule_of_40'), pct=False)}")
    lines.append(f"SGA Efficiency:          {_fmt(cyber_raw.get('sga_eff'), pct=True)}")
    lines.append(f"R&D Efficiency:          {_fmt(cyber_raw.get('rd_eff'), pct=True)}\n")

    # VALUATION
    lines.append("VALUATION SNAPSHOT")
    lines.append("----------------------------------------------")
    lines.append(f"P/E Ratio:               {_fmt(val.get('pe'))}")
    lines.append(f"PEG Ratio:               {_fmt(val.get('peg'))}")
    lines.append(f"Price/Sales:             {_fmt(val.get('ps'))}")
    lines.append(f"Price/Book:              {_fmt(val.get('pb'))}")
    lines.append(f"FCF Yield:               {_fmt(val.get('fcf_yield'), pct=True)}\n")

    lines.append("==============================================")

    return "\n".join(lines)
