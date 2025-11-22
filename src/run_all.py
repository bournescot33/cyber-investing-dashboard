from src.analyze_company import analyze_company
from src.tickers import WATCHLIST

def run_all():
    for sym in WATCHLIST:
        print(analyze_company(sym))
        print("\n\n")

if __name__ == "__main__":
    run_all()
