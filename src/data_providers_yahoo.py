import yfinance as yf
import pandas as pd

def get_yahoo_financials(symbol: str) -> dict:
    """
    Fetches financial statements from Yahoo Finance via yfinance.
    Returns a dictionary containing:
        - income statement (annual & quarterly)
        - balance sheet
        - cash flow
        - earnings history
        - valuation metrics
    """
    ticker = yf.Ticker(symbol)

    # Yahoo financials come with dates as columns; we transpose them to rows.
    income = ticker.financials.T
    balance = ticker.balance_sheet.T
    cashflow = ticker.cashflow.T
    # `Ticker.earnings` is deprecated and may be unavailable via the API.
    # Derive an earnings series (Net Income) from the fetched income statements
    # when possible, and fall back to quarterly financials for quarterly earnings.
    earnings = None
    if isinstance(income, pd.DataFrame):
        for colname in ("Net Income", "netIncome", "NetIncome"):
            if colname in income.columns:
                earnings = income[[colname]].rename(columns={colname: "Net Income"})
                break

    quarterly_earnings = None
    try:
        q_fin = ticker.quarterly_financials
        if q_fin is not None and hasattr(q_fin, "T"):
            q_fin_t = q_fin.T
            for colname in ("Net Income", "netIncome", "NetIncome"):
                if colname in q_fin_t.columns:
                    quarterly_earnings = q_fin_t[[colname]].rename(columns={colname: "Net Income"})
                    break
    except Exception:
        quarterly_earnings = None

    # Analyst estimates (for forward P/E, EPS estimates, etc.)
    try:
        analysis = ticker.analysis
    except Exception:
        analysis = None

    return {
        "income": income,
        "balance": balance,
        "cashflow": cashflow,
        "earnings": earnings,
        "quarterly_earnings": quarterly_earnings,
        "analysis": analysis,
    }


def get_current_price(symbol: str) -> float:
    ticker = yf.Ticker(symbol)
    df = ticker.history(period="1d")
    return float(df["Close"].iloc[-1])


def get_yahoo_key_metrics(symbol: str) -> dict:
    """
    Returns key valuation ratios and metrics using yfinance's built-in info.
    includes: trailingPE, forwardPE, priceToBook, profitMargins, etc.
    """
    ticker = yf.Ticker(symbol)
    info = ticker.info  # this contains dozens of valuation fields
    return info
