import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('backend'))

from services.providers.akshare_provider import get_fund_quote, get_a_stock_quote

def test_expanded_assets():
    # 1. Test Funds
    fund_symbols = ['510300', '159915', '000001'] # ETF, ETF, Open Fund
    print("--- Testing Funds ---")
    for sym in fund_symbols:
        print(f"Fetching fund quote for {sym}...")
        try:
            quote = get_fund_quote(sym)
            print(f"Result: {quote}")
        except Exception as e:
            print(f"Error for {sym}: {e}")

    # 2. Test BJ Stocks
    bj_symbols = ['830833', '430047']
    print("\n--- Testing BJ Stocks ---")
    for sym in bj_symbols:
        print(f"Fetching BJ stock quote for {sym}...")
        try:
            quote = get_a_stock_quote(sym)
            print(f"Result: {quote}")
        except Exception as e:
            print(f"Error for {sym}: {e}")

if __name__ == "__main__":
    test_expanded_assets()
