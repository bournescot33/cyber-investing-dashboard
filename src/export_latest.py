import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd

from src.tickers import PURE_PLAY_CYBER, CLOUD_SECURITY_LEADERS
from src.quality import compute_quality_metrics, score_quality
from src.quality_cyber import compute_cyber_metrics, score_cyber_styles
from src.analyze_company import get_basic_valuation


def build_row(symbol: str, bucket: str) -> dict:
    """Compute all metrics for one symbol and return as a flat dict."""
    # Use Eastern Time (US/Eastern) timezone-aware timestamp (EST/EDT)
    # zoneinfo handles DST automatically.
    timestamp = datetime.now(ZoneInfo("America/New_York")).isoformat()

    # Universal quality (Buffett/Munger style)
    base_metrics = compute_quality_metrics(symbol)
    base_score = score_quality(base_metrics)

    # Cyber metrics + styles
    cyber_raw = compute_cyber_metrics(symbol)
    cyber_scores = score_cyber_styles(cyber_raw)

    # Valuation
    val = get_basic_valuation(symbol)

    row = {
        "timestamp_utc": timestamp,
        "symbol": symbol,
        "bucket": bucket,  # "pure_play" or "cloud_leader"

        # Universal quality metrics
        "quality_score": base_score.get("quality_score"),
        "roic": base_metrics.get("roic"),
        "gross_margin": base_metrics.get("gross_margin"),
        "net_margin": base_metrics.get("net_margin"),
        "revenue_cagr": base_metrics.get("revenue_cagr"),
        "fcf_cagr": base_metrics.get("fcf_cagr"),

        # Cyber scores
        "growth_score": cyber_scores.get("growth_score"),
        "profitability_score": cyber_scores.get("profitability_score"),
        "balanced_score": cyber_scores.get("balanced_score"),

        # Cyber raw metrics
        "arr_growth": cyber_raw.get("arr_growth"),
        "gross_margin_avg": cyber_raw.get("gross_margin_avg"),
        "gross_margin_trend": cyber_raw.get("gross_margin_trend"),
        "fcf_margin": cyber_raw.get("fcf_margin"),
        "rule_of_40": cyber_raw.get("rule_of_40"),
        "sga_eff": cyber_raw.get("sga_eff"),
        "rd_eff": cyber_raw.get("rd_eff"),

        # Valuation snapshot
        "pe": val.get("pe"),
        "peg": val.get("peg"),
        "ps": val.get("ps"),
        "pb": val.get("pb"),
        "fcf_yield": val.get("fcf_yield"),
    }

    return row


def main():
    rows = []

    for sym in PURE_PLAY_CYBER:
        rows.append(build_row(sym, bucket="pure_play"))

    for sym in CLOUD_SECURITY_LEADERS:
        rows.append(build_row(sym, bucket="cloud_leader"))

    df = pd.DataFrame(rows)

    # Ensure data folder exists
    os.makedirs("data", exist_ok=True)
    out_path = os.path.join("data", "latest_scores.csv")
    df.to_csv(out_path, index=False)
    print(f"Wrote latest scores for {len(rows)} tickers to {out_path}")


if __name__ == "__main__":
    main()
