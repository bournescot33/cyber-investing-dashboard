import numpy as np
from typing import Dict, Any

from .data_providers_yahoo import get_yahoo_financials
from .sec_scraper import get_rd_sga_from_10k_url


def _safe_cagr(start: float, end: float, years: int) -> float:
    if years <= 0:
        return np.nan
    if start <= 0 or end <= 0:
        return np.nan
    return (end / start) ** (1 / years) - 1


def _first_existing_column(df, candidates):
    """
    Return the first column from candidates that exists in df.columns.
    If none exist, return None.
    """
    for col in candidates:
        if col in df.columns:
            return col
    return None


# Optional: map tickers to their 10-K HTML URLs for SEC fallback.
# You fill in the URLs you care about.
TEN_K_URLS = {
    # Example (replace with real URLs from SEC EDGAR or IR):
    # "CRWD": "https://www.sec.gov/Archives/edgar/data/1535527/000153552725000009/crwd-20250131.htm",
    # "PANW": "https://www.sec.gov/ixviewer/doc?action=load&doc=/Archives/edgar/data/0001327567/...htm",
    # "FTNT": "...",
    # "NET":  "...",
    # "ZS":   "...",
}


def compute_cyber_metrics(symbol: str) -> Dict[str, Any]:
    """
    Compute cybersecurity-specific business quality metrics using Yahoo Finance data.
    Fallback to SEC 10-K scraping for R and D and Sales and Marketing
    when Yahoo does not provide those line items.

    Metrics:
      - arr_growth: revenue CAGR (proxy for ARR growth)
      - gross_margin_avg: average gross margin over recent years
      - gross_margin_trend: change in gross margin over recent years
      - fcf_margin: latest free cash flow margin
      - rule_of_40: growth% + FCF margin%
      - sga_eff: Sales and Marketing as % of revenue
      - rd_eff: Research and Development as % of revenue
    """
    data = get_yahoo_financials(symbol)
    income = data["income"].sort_index()      # rows = periods, columns = income items
    cashflow = data["cashflow"].sort_index()  # rows = periods, columns = cashflow items

    # --- Revenue series (ARR growth proxy) ---
    if "Total Revenue" in income.columns:
        rev_series = income["Total Revenue"].dropna()
    else:
        rev_series = None

    if rev_series is not None and len(rev_series) >= 2:
        rev_6 = rev_series.tail(6)
        arr_growth = _safe_cagr(rev_6.iloc[0], rev_6.iloc[-1], len(rev_6) - 1)
    else:
        arr_growth = np.nan

    # --- Gross margin level and trend ---
    if "Gross Profit" in income.columns and "Total Revenue" in income.columns:
        gm_series = (income["Gross Profit"] / income["Total Revenue"].replace(0, np.nan)).dropna()
        gm_5 = gm_series.tail(5)
        if len(gm_5) >= 2:
            gross_margin_avg = gm_5.mean()
            gross_margin_trend = gm_5.iloc[-1] - gm_5.iloc[0]
        else:
            gross_margin_avg = np.nan
            gross_margin_trend = np.nan
    else:
        gross_margin_avg = np.nan
        gross_margin_trend = np.nan

    # --- FCF margin (Operating CF + Capex) ---
    if (
        "Operating Cash Flow" in cashflow.columns
        and "Capital Expenditure" in cashflow.columns
        and "Total Revenue" in income.columns
    ):
        ocf_latest = cashflow["Operating Cash Flow"].dropna().tail(1)
        capex_latest = cashflow["Capital Expenditure"].dropna().tail(1)
        rev_latest_cf = income["Total Revenue"].dropna().tail(1)

        if len(ocf_latest) == 1 and len(capex_latest) == 1 and len(rev_latest_cf) == 1:
            fcf_latest = ocf_latest.iloc[0] + capex_latest.iloc[0]
            fcf_margin = fcf_latest / rev_latest_cf.iloc[0] if rev_latest_cf.iloc[0] != 0 else np.nan
        else:
            fcf_margin = np.nan
    else:
        fcf_margin = np.nan

    # --- Rule of 40 ---
    if not np.isnan(arr_growth) and not np.isnan(fcf_margin):
        rule_of_40 = arr_growth * 100 + fcf_margin * 100
    else:
        rule_of_40 = np.nan

    # --- S and M efficiency: Sales and Marketing / revenue ---
    sga_col = _first_existing_column(
        income,
        [
            "Selling General Administrative",
            "SellingGeneralAdministrative",
            "Sales General Administrative",
            "SG&A",
            "Selling, General & Administrative",
        ],
    )

    if sga_col is not None and "Total Revenue" in income.columns:
        sga_latest = income[sga_col].dropna().tail(1)
        rev_latest = income["Total Revenue"].dropna().tail(1)
        if len(sga_latest) == 1 and len(rev_latest) == 1 and rev_latest.iloc[0] != 0:
            sga_eff = sga_latest.iloc[0] / rev_latest.iloc[0]
        else:
            sga_eff = np.nan
    else:
        sga_eff = np.nan

    # --- R and D efficiency: R and D / revenue ---
    rd_col = _first_existing_column(
        income,
        [
            "Research Development",
            "ResearchAndDevelopment",
            "ResearchAndDevelopmentExpenses",
            "Research & Development",
            "R D",
        ],
    )

    if rd_col is not None and "Total Revenue" in income.columns:
        rd_latest = income[rd_col].dropna().tail(1)
        rev_latest = income["Total Revenue"].dropna().tail(1)
        if len(rd_latest) == 1 and len(rev_latest) == 1 and rev_latest.iloc[0] != 0:
            rd_eff = rd_latest.iloc[0] / rev_latest.iloc[0]
        else:
            rd_eff = np.nan
    else:
        rd_eff = np.nan

    # --- SEC 10-K fallback for R and D and Sales and Marketing if missing ---
    if symbol in TEN_K_URLS and (np.isnan(sga_eff) or np.isnan(rd_eff)):
        url = TEN_K_URLS[symbol]
        try:
            rd_val, sga_val = get_rd_sga_from_10k_url(url)
            if "Total Revenue" in income.columns:
                rev_latest = income["Total Revenue"].dropna().tail(1)
                if len(rev_latest) == 1 and rev_latest.iloc[0] != 0:
                    if np.isnan(rd_eff) and rd_val is not None:
                        rd_eff = rd_val / rev_latest.iloc[0]
                    if np.isnan(sga_eff) and sga_val is not None:
                        sga_eff = sga_val / rev_latest.iloc[0]
        except Exception as e:
            print(f"SEC fallback for {symbol} failed: {e}")

    return {
        "arr_growth": arr_growth,
        "gross_margin_avg": gross_margin_avg,
        "gross_margin_trend": gross_margin_trend,
        "fcf_margin": fcf_margin,
        "rule_of_40": rule_of_40,
        "sga_eff": sga_eff,
        "rd_eff": rd_eff,
    }


def score_cyber_styles(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute three different cyber quality scores from the same metrics:

      - growth_score        growth heavy
      - profitability_score profitability heavy
      - balanced_score      middle ground

    All scores are normalized to 0 to 100.
    """
    arr = metrics.get("arr_growth", np.nan)
    gm = metrics.get("gross_margin_avg", np.nan)
    gm_tr = metrics.get("gross_margin_trend", np.nan)
    fcf_m = metrics.get("fcf_margin", np.nan)
    r40 = metrics.get("rule_of_40", np.nan)
    sga = metrics.get("sga_eff", np.nan)
    rd = metrics.get("rd_eff", np.nan)

    # ---- Growth heavy score ----
    g_score = 0
    g_max = 0

    # Rule of 40 (40 points)
    g_max += 40
    if not np.isnan(r40):
        if r40 >= 60:
            g_score += 40
        elif r40 >= 50:
            g_score += 32
        elif r40 >= 40:
            g_score += 24
        elif r40 >= 30:
            g_score += 16
        elif r40 >= 20:
            g_score += 8

    # ARR growth (40 points)
    g_max += 40
    if not np.isnan(arr):
        if arr >= 0.35:
            g_score += 40
        elif arr >= 0.25:
            g_score += 32
        elif arr >= 0.18:
            g_score += 24
        elif arr >= 0.12:
            g_score += 16
        elif arr >= 0.08:
            g_score += 8

    # Gross margin level sanity (20 points)
    g_max += 20
    if not np.isnan(gm):
        if gm >= 0.80:
            g_score += 20
        elif gm >= 0.75:
            g_score += 16
        elif gm >= 0.70:
            g_score += 12
        elif gm >= 0.65:
            g_score += 8

    growth_score = round(100 * g_score / g_max) if g_max > 0 else np.nan

    # ---- Profitability heavy score ----
    p_score = 0
    p_max = 0

    # FCF margin (40 points)
    p_max += 40
    if not np.isnan(fcf_m):
        if fcf_m >= 0.30:
            p_score += 40
        elif fcf_m >= 0.20:
            p_score += 32
        elif fcf_m >= 0.15:
            p_score += 24
        elif fcf_m >= 0.10:
            p_score += 16
        elif fcf_m >= 0.05:
            p_score += 8

    # Gross margin (30 points)
    p_max += 30
    if not np.isnan(gm):
        if gm >= 0.80:
            p_score += 30
        elif gm >= 0.75:
            p_score += 24
        elif gm >= 0.70:
            p_score += 18
        elif gm >= 0.65:
            p_score += 12

    # S and M efficiency (15 points) lower is better
    p_max += 15
    if not np.isnan(sga):
        if sga <= 0.30:
            p_score += 15
        elif sga <= 0.40:
            p_score += 12
        elif sga <= 0.50:
            p_score += 9
        elif sga <= 0.60:
            p_score += 6

    # R and D efficiency (15 points) like 10 to 20 percent best
    p_max += 15
    if not np.isnan(rd):
        if 0.10 <= rd <= 0.20:
            p_score += 15
        elif 0.08 <= rd < 0.10 or 0.20 < rd <= 0.25:
            p_score += 12
        elif 0.05 <= rd < 0.08 or 0.25 < rd <= 0.30:
            p_score += 9

    profitability_score = round(100 * p_score / p_max) if p_max > 0 else np.nan

    # ---- Balanced score ----
    # About one third growth, one third profitability, one third efficiency
    b_score = 0
    b_max = 0

    # Growth component (35 points)
    b_max += 35
    growth_component = 0
    growth_component_max = 0

    growth_component_max += 20  # Rule of 40
    if not np.isnan(r40):
        if r40 >= 60:
            growth_component += 20
        elif r40 >= 50:
            growth_component += 16
        elif r40 >= 40:
            growth_component += 12
        elif r40 >= 30:
            growth_component += 8

    growth_component_max += 15  # ARR
    if not np.isnan(arr):
        if arr >= 0.30:
            growth_component += 15
        elif arr >= 0.20:
            growth_component += 12
        elif arr >= 0.12:
            growth_component += 9
        elif arr >= 0.08:
            growth_component += 6

    if growth_component_max > 0:
        b_score += 35 * (growth_component / growth_component_max)

    # Profitability component (35 points)
    b_max += 35
    prof_component = 0
    prof_component_max = 0

    prof_component_max += 20  # FCF
    if not np.isnan(fcf_m):
        if fcf_m >= 0.25:
            prof_component += 20
        elif fcf_m >= 0.18:
            prof_component += 16
        elif fcf_m >= 0.12:
            prof_component += 12
        elif fcf_m >= 0.07:
            prof_component += 8

    prof_component_max += 15  # GM
    if not np.isnan(gm):
        if gm >= 0.78:
            prof_component += 15
        elif gm >= 0.73:
            prof_component += 12
        elif gm >= 0.68:
            prof_component += 9
        elif gm >= 0.63:
            prof_component += 6

    if prof_component_max > 0:
        b_score += 35 * (prof_component / prof_component_max)

    # Efficiency component (30 points) SGA, RD, GM trend
    b_max += 30
    eff_component = 0
    eff_component_max = 0

    eff_component_max += 10  # SGA
    if not np.isnan(sga):
        if sga <= 0.35:
            eff_component += 10
        elif sga <= 0.45:
            eff_component += 8
        elif sga <= 0.55:
            eff_component += 6

    eff_component_max += 10  # RD
    if not np.isnan(rd):
        if 0.10 <= rd <= 0.20:
            eff_component += 10
        elif 0.08 <= rd < 0.10 or 0.20 < rd <= 0.25:
            eff_component += 8
        elif 0.05 <= rd < 0.08 or 0.25 < rd <= 0.30:
            eff_component += 6

    eff_component_max += 10  # GM trend
    if not np.isnan(gm_tr):
        if gm_tr >= 0.03:
            eff_component += 10
        elif gm_tr >= 0.02:
            eff_component += 8
        elif gm_tr >= 0.01:
            eff_component += 6

    if eff_component_max > 0:
        b_score += 30 * (eff_component / eff_component_max)

    balanced_score = round(100 * b_score / b_max) if b_max > 0 else np.nan

    return {
        **metrics,
        "growth_score": growth_score,
        "profitability_score": profitability_score,
        "balanced_score": balanced_score,
    }
