import sys
import os

# Add backend to path
sys.path.append(os.path.abspath('backend'))

from services.providers.akshare_provider import get_fund_quote, get_a_stock_quote

def test_simplified():
    print("--- Testing A-Stock (600519贵州茅台) ---")
    try:
        quote = get_a_stock_quote('600519')
        print(f"Result: {quote}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n--- Testing ETF (510300) ---")
    try:
        quote = get_fund_quote('510300')
        print(f"Result: {quote}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_simplified()
