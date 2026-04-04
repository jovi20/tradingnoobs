import akshare as ak
from backend.services.providers.akshare_provider import get_fund_quote

# Test LOF Fund
lof_symbol = "161725" # 招商中证白酒指数(LOF)A
print(f"Testing LOF Fund ({lof_symbol})...")

try:
    lof_data = get_fund_quote(lof_symbol)
    print(f"LOF Result:\n{lof_data}")
except Exception as e:
    print(f"LOF Error: {e}")

# Test ETF Fund (Regression)
etf_symbol = "510300" # 沪深300ETF
print(f"\nTesting ETF Fund ({etf_symbol})...")
try:
    etf_data = get_fund_quote(etf_symbol)
    print(f"ETF Result:\n{etf_data}")
except Exception as e:
    print(f"ETF Error: {e}")
