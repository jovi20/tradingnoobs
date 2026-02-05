import akshare as ak
import pandas as pd

def debug_akshare():
    print("Testing fund_etf_spot_em...")
    try:
        df = ak.fund_etf_spot_em()
        print(f"ETF Columns: {df.columns.tolist()}")
        print(f"First row: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"ETF error: {e}")

    print("\nTesting fund_em_open_fund_daily...")
    try:
        df = ak.fund_em_open_fund_daily()
        print(f"Open Fund Columns: {df.columns.tolist()}")
        print(f"First row: {df.iloc[0].to_dict()}")
    except Exception as e:
        print(f"Open fund error: {e}")

if __name__ == "__main__":
    debug_akshare()
