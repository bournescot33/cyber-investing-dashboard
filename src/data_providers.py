import requests
import pandas as pd
from typing import Dict, Any, Optional

from .config import FMP_API_KEY

# Updated base URL for the new FMP "stable" API
BASE_URL = "https://financialmodelingprep.com/stable"


def _get(endpoint: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """
    Internal helper function.
    Builds the URL, attaches the API key, sends the request,
    and returns the parsed JSON.
    """
    if params is None:
        params = {}

    # Always add the API key from config.py
    params["apikey"] = FMP_API_KEY

    url = f"{BASE_URL}/{endpoint}"
    response = requests.get(url, params=params)
    response.raise_for_status()  # raise an error if the request failed
    return response.json()


def get_company_profile(symbol: str) -> Dict[str, Any]:
    """
    Get basic company information for a ticker symbol.
    Uses the new stable profile endpoint:
      https://financialmodelingprep.com/stable/profile?symbol=AAPL
    """
    data = _get("profile", {"symbol": symbol})
    return data[0] if data else {}


def get_income_statements(symbol: str, period: str = "annual", limit: int = 10) -> pd.DataFrame:
    """
    Get historical income statements for a company as a pandas DataFrame.

    Endpoint:
      https://financialmodelingprep.com/stable/income-statement?symbol=AAPL

    FMP uses 'period' and 'limit' as query params.
    """
    params = {"symbol": symbol, "period": period, "limit": limit}
    data = _get("income-statement", params)
    return pd.DataFrame(data)


def get_balance_sheets(symbol: str, period: str = "annual", limit: int = 10) -> pd.DataFrame:
    """
    Get historical balance sheets as a DataFrame.

    Endpoint:
      https://financialmodelingprep.com/stable/balance-sheet-statement?symbol=AAPL
    """
    params = {"symbol": symbol, "period": period, "limit": limit}
    data = _get("balance-sheet-statement", params)
    return pd.DataFrame(data)


def get_cash_flows(symbol: str, period: str = "annual", limit: int = 10) -> pd.DataFrame:
    """
    Get historical cash flow statements as a DataFrame.

    Endpoint:
      https://financialmodelingprep.com/stable/cash-flow-statement?symbol=AAPL
    """
    params = {"symbol": symbol, "period": period, "limit": limit}
    data = _get("cash-flow-statement", params)
    return pd.DataFrame(data)


def get_key_metrics(symbol: str, period: str = "annual", limit: int = 10) -> pd.DataFrame:
    """
    Get key fundamental metrics, like ROIC, margins, etc.

    Endpoint:
      https://financialmodelingprep.com/stable/key-metrics?symbol=AAPL
    """
    params = {"symbol": symbol, "period": period, "limit": limit}
    data = _get("key-metrics", params)
    return pd.DataFrame(data)


def get_ratios(symbol: str, period: str = "annual", limit: int = 10) -> pd.DataFrame:
    """
    Get financial ratios, like current ratio, quick ratio, etc.

    Endpoint:
      https://financialmodelingprep.com/stable/ratios?symbol=AAPL
    """
    params = {"symbol": symbol, "period": period, "limit": limit}
    data = _get("ratios", params)
    return pd.DataFrame(data)


def get_historical_prices(symbol: str, variant: str = "full") -> pd.DataFrame:
    """
    Get daily historical prices for a company.

    Endpoints (variant):
      light: https://financialmodelingprep.com/stable/historical-price-eod/light?symbol=AAPL
      full:  https://financialmodelingprep.com/stable/historical-price-eod/full?symbol=AAPL

    Default is 'full' for richer data.
    """
    if variant not in ("light", "full"):
        raise ValueError("variant must be 'light' or 'full'")

    endpoint = f"historical-price-eod/{variant}"
    data = _get(endpoint, {"symbol": symbol})
    # For the historical price APIs, the response is already a list of records
    return pd.DataFrame(data)

