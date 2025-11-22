import re
from typing import Optional, Tuple

import requests
from bs4 import BeautifulSoup


# You can set a default User-Agent for SEC requests (SEC strongly prefers this)
DEFAULT_HEADERS = {
    "User-Agent": "yourname@example.com Python SEC scraper"
}


def fetch_10k_html(url: str) -> str:
    """
    Fetch raw HTML for a given 10-K filing URL.

    For now, you will provide the URL manually (from SEC EDGAR or company IR site).
    Later this can be automated to always grab the latest 10-K for a ticker.
    """
    resp = requests.get(url, headers=DEFAULT_HEADERS)
    resp.raise_for_status()
    return resp.text


def _parse_numeric(text: str) -> Optional[float]:
    """
    Parse a string like '1,234,000' or '(1,234)' into a float.
    Returns None if parsing fails.
    """
    if text is None:
        return None

    t = text.strip()

    if not t:
        return None

    # Handle parentheses as negatives
    negative = t.startswith("(") and t.endswith(")")
    t = t.strip("()")

    # Remove commas and other junk
    t = re.sub(r"[^0-9.\-]", "", t)

    if not t:
        return None

    try:
        value = float(t)
        if negative:
            value = -value
        return value
    except ValueError:
        return None


def extract_rd_sga_from_10k_html(html: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Given the raw HTML of a 10-K (or similar annual report),
    try to locate the Consolidated Statements of Operations table
    and extract the most recent year values for:
      - Research and Development
      - Sales and Marketing (or Sales and marketing, Selling and marketing, etc.)

    Returns (rd_value, sga_value) in the same units as shown in the filing
    (usually thousands or millions), or (None, None) if not found.
    """
    soup = BeautifulSoup(html, "lxml")

    # Candidate row label patterns
    rd_patterns = [
        re.compile(r"research\s+and\s+development", re.I),
        re.compile(r"research\s+&\s+development", re.I),
        re.compile(r"research\s+and\s+product\s+development", re.I),
    ]

    sga_patterns = [
        re.compile(r"sales\s+and\s+marketing", re.I),
        re.compile(r"selling\s+and\s+marketing", re.I),
        re.compile(r"sales\s+and\s+advertising", re.I),
        re.compile(r"sales\s+and\s+promotion", re.I),
    ]

    rd_value = None
    sga_value = None

    # Look through all tables
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all(["td", "th"])
            if len(cells) < 2:
                continue

            row_label = cells[0].get_text(" ", strip=True)

            if not row_label:
                continue

            # Check for R&D
            if rd_value is None:
                if any(p.search(row_label) for p in rd_patterns):
                    # Try last numeric cell in the row as the most recent year
                    numeric_cells = cells[1:]
                    numeric_values = [
                        _parse_numeric(c.get_text(" ", strip=True)) for c in numeric_cells
                    ]
                    numeric_values = [v for v in numeric_values if v is not None]
                    if numeric_values:
                        rd_value = numeric_values[0]  # could also choose last, depends on layout

            # Check for Sales and Marketing
            if sga_value is None:
                if any(p.search(row_label) for p in sga_patterns):
                    numeric_cells = cells[1:]
                    numeric_values = [
                        _parse_numeric(c.get_text(" ", strip=True)) for c in numeric_cells
                    ]
                    numeric_values = [v for v in numeric_values if v is not None]
                    if numeric_values:
                        sga_value = numeric_values[0]

            if rd_value is not None and sga_value is not None:
                break
        if rd_value is not None and sga_value is not None:
            break

    return rd_value, sga_value


def get_rd_sga_from_10k_url(url: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Convenience function:
      1) Downloads 10-K HTML from the given URL
      2) Parses out R&D and Sales and Marketing values
    """
    html = fetch_10k_html(url)
    return extract_rd_sga_from_10k_html(html)
