import os
import pandas as pd
import streamlit as st
import altair as alt
import yfinance as yf

DATA_PATH = os.path.join("data", "latest_scores.csv")


# ---------------------------------------------------------
# Load Data
# ---------------------------------------------------------
def load_data():
    if not os.path.exists(DATA_PATH):
        st.error(f"Could not find {DATA_PATH}. Run the export script first.")
        return None
    df = pd.read_csv(DATA_PATH)
    return df


# ---------------------------------------------------------
# Add valuation signals (Cheap / Neutral / Expensive)
# ---------------------------------------------------------
def add_valuation_signals(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Rank PS (lower PS = cheaper)
    if "ps" in df.columns:
        df["ps_rank"] = (1 - df["ps"].rank(pct=True)).fillna(0.5)
    else:
        df["ps_rank"] = 0.5

    # Rank PE (lower PE = cheaper)
    if "pe" in df.columns:
        df["pe_rank"] = (1 - df["pe"].rank(pct=True)).fillna(0.5)
    else:
        df["pe_rank"] = 0.5

    # Rank FCF yield (higher = cheaper)
    if "fcf_yield" in df.columns:
        df["fcf_rank"] = df["fcf_yield"].rank(pct=True).fillna(0.5)
    else:
        df["fcf_rank"] = 0.5

    # Blended score
    df["valuation_score"] = df[["ps_rank", "pe_rank", "fcf_rank"]].mean(axis=1)

    # Assign buckets by quantile cutoffs
    cheap_thr = df["valuation_score"].quantile(0.66)
    exp_thr = df["valuation_score"].quantile(0.33)

    def bucket(v):
        if v >= cheap_thr:
            return "Cheap"
        if v <= exp_thr:
            return "Expensive"
        return "Neutral"

    df["valuation_bucket"] = df["valuation_score"].apply(bucket)
    return df


# ---------------------------------------------------------
# Main Dashboard
# ---------------------------------------------------------
def main():
    st.set_page_config(page_title="Cyber Investing Dashboard", layout="wide")
    st.title("Cybersecurity Investing Dashboard")

    # ---------------------------------
    # Load and prepare data
    # ---------------------------------
    df = load_data()
    if df is None or df.empty:
        st.stop()

    df = add_valuation_signals(df)

    # ---------------------------------
    # Top-level filters
    # ---------------------------------
    bucket = st.selectbox(
        "Select bucket",
        options=["All", "Pure Play Cyber", "Cloud / Platform Leaders"],
        index=0,
    )

    filtered = df.copy()

    if bucket == "Pure Play Cyber":
        filtered = filtered[filtered["bucket"] == "pure_play"]
    elif bucket == "Cloud / Platform Leaders":
        filtered = filtered[filtered["bucket"] == "cloud_leader"]

    # ---------------------------------
    # FINANCIAL SNAPSHOT (New)
    # ---------------------------------
    st.subheader("Financial Snapshot")

    ticker_choice = st.selectbox(
        "Select a ticker for fundamental details:",
        options=filtered["symbol"].sort_values().unique(),
    )

    t = yf.Ticker(ticker_choice)
    info = t.info

    def fmt(x):
        if x is None or x != x:
            return "—"
        if isinstance(x, (int, float)):
            if abs(x) > 1_000_000_000:
                return f"{x/1_000_000_000:.2f} B"
            if abs(x) > 1_000_000:
                return f"{x/1_000_000:.2f} M"
            return f"{x:.2f}"
        return str(x)

    col1, col2, col3, col4 = st.columns(4)
    col5, col6, col7, col8 = st.columns(4)

    col1.metric("Price", fmt(info.get("currentPrice")))
    col2.metric("Market Cap", fmt(info.get("marketCap")))
    col3.metric("EPS (TTM)", fmt(info.get("trailingEps")))
    col4.metric("P/E (TTM)", fmt(info.get("trailingPE")))

    col5.metric("Price/Sales", fmt(info.get("priceToSalesTrailing12Months")))
    col6.metric("Price/Book", fmt(info.get("priceToBook")))
    col7.metric("Revenue (TTM)", fmt(info.get("totalRevenue")))
    col8.metric("Free Cash Flow", fmt(info.get("freeCashflow")))

    st.markdown("---")

    # ---------------------------------
    # Score & Valuation Table
    # ---------------------------------
    st.subheader("Score & Valuation Table")

    score_cols = [
        "symbol",
        "bucket",
        "quality_score",
        "growth_score",
        "profitability_score",
        "balanced_score",
        "arr_growth",
        "fcf_margin",
        "rule_of_40",
        "pe",
        "ps",
        "pb",
        "fcf_yield",
        "valuation_score",
        "valuation_bucket",
    ]

    existing_cols = [c for c in score_cols if c in filtered.columns]

    st.dataframe(
        filtered[existing_cols].sort_values("symbol").reset_index(drop=True)
    )
    # ---------------------------------
    # Legend / Interpretation
    # ---------------------------------
    with st.expander("How to interpret these scores and valuation signals"):
        st.markdown(
            """
**Scores**

- `quality_score`  
  Overall fundamental quality on a 0–100 scale.  
  Rough mental model:  
  - **0–40** → weaker fundamentals / inconsistent profitability  
  - **40–70** → decent business, improving or stable  
  - **70–100** → high-quality business with strong margins and growth

- `growth_score`  
  Focuses on revenue/ARR growth, Rule of 40, and improving gross margins.  
  - Higher = faster, more durable growth  

- `profitability_score`  
  Focuses on free cash flow margin and efficiency.  
  - Higher = stronger current profitability

- `balanced_score`  
  Blends growth and profitability into a single “quality of earnings” view.  
  - Higher = better balance of growth and cash generation

**Key Metrics**

- `arr_growth` → Growth in revenue/ARR; higher is better.  
- `fcf_margin` → Free cash flow as a % of revenue; higher is better.  
- `rule_of_40` → `growth + fcf_margin`. Cyber SaaS names above **40** are usually considered strong.

**Valuation**

- `valuation_score` (higher = cheaper **relative to this universe**)  
  Combines ranks for:
  - Price/Sales (lower better)
  - P/E (lower better)
  - FCF Yield (higher better)

- `valuation_bucket`  
  - **Cheap** → trades towards the lower end of valuations in this group  
  - **Neutral** → around the middle of the pack  
  - **Expensive** → trades towards the higher end of valuations in this group
"""
        )

    st.markdown("---")

    # ---------------------------------
    # Growth vs Profitability Scatter
    # ---------------------------------
    st.subheader("Growth vs Profitability")

    scatter_df = filtered.dropna(subset=["growth_score", "profitability_score"])

    if not scatter_df.empty:
        chart1 = alt.Chart(scatter_df).mark_circle(size=120).encode(
            x=alt.X("growth_score:Q", title="Growth Score"),
            y=alt.Y("profitability_score:Q", title="Profitability Score"),
            color=alt.Color(
                "valuation_bucket:N",
                title="Valuation",
                scale=alt.Scale(
                    domain=["Cheap", "Neutral", "Expensive"],
                    range=["#2ca02c", "#ffbf00", "#d62728"],
                ),
            ),
            tooltip=[
                "symbol",
                "bucket",
                "growth_score",
                "profitability_score",
                "balanced_score",
                "valuation_bucket",
            ],
        )
        st.altair_chart(chart1, use_container_width=True)
    else:
        st.info("Not enough data for growth vs profitability chart.")
        st.markdown(
            """
**How to read this:**

- Each point is a ticker.  
- **Right** = higher growth score (faster or more durable growth).  
- **Up** = higher profitability score (better free cash flow and margin profile).  
- **Colors**:  
  - 🟢 **Cheap** → more attractive valuation vs peers  
  - 🟡 **Neutral** → middle of the pack  
  - 🔴 **Expensive** → richer valuation vs peers
"""
        )

    st.markdown("---")

    # ---------------------------------
    # Valuation vs Growth Quadrant
    # ---------------------------------
    st.subheader("Valuation vs Growth Quadrant")

    quad_df = filtered.dropna(subset=["growth_score", "valuation_score"])

    if not quad_df.empty:
        gx_med = quad_df["growth_score"].median()
        val_med = quad_df["valuation_score"].median()

        base = alt.Chart(quad_df)

        points = base.mark_circle(size=140).encode(
            x=alt.X("growth_score:Q", title="Growth Score"),
            y=alt.Y("valuation_score:Q", title="Valuation Score (higher = cheaper)"),
            color=alt.Color(
                "valuation_bucket:N",
                title="Valuation",
                scale=alt.Scale(
                    domain=["Cheap", "Neutral", "Expensive"],
                    range=["#2ca02c", "#ffbf00", "#d62728"],
                ),
            ),
            tooltip=[
                "symbol",
                "bucket",
                "growth_score",
                "valuation_score",
                "valuation_bucket",
            ],
        )

        # Quadrant lines
        vline = alt.Chart(pd.DataFrame({"x": [gx_med]})).mark_rule(strokeDash=[4, 4]).encode(x="x:Q")
        hline = alt.Chart(pd.DataFrame({"y": [val_med]})).mark_rule(strokeDash=[4, 4]).encode(y="y:Q")

        st.altair_chart(points + vline + hline, use_container_width=True)

        st.markdown("""
**Quadrant Interpretation**
- **Top-Right** → High growth, cheap valuation (best hunting ground)
- **Top-Left** → Lower growth, cheap valuation
- **Bottom-Right** → High growth, expensive valuation
- **Bottom-Left** → Lower growth, expensive valuation
""")
    else:
        st.info("Not enough data for quadrant chart.")

    st.markdown("---")
    st.caption("Data source: Yahoo Finance via yfinance; scores computed in your local pipeline.")


if __name__ == "__main__":
    main()
