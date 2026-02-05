import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('backend'))

from services.providers.akshare_provider import get_fund_quote, get_a_stock_quote

def test_robustness():
    # Test a fund that often fails in bulk
    print("--- Testing Fund (510300) with fallbacks ---")
    try:
        quote = get_fund_quote('510300')
        print(f"Result: {quote}")
    except Exception as e:
        print(f"Error: {e}")

    # Test an open end fund
    print("\n--- Testing Open Fund (000001) ---")
    try:
        quote = get_fund_quote('000001')
        print(f"Result: {quote}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_robustness()
