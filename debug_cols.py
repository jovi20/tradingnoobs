import akshare as ak
import pandas as pd

def debug_columns():
    print("--- ETF Spot ---")
    try:
        df = ak.fund_etf_spot_em()
        print(f"Columns: {df.columns.tolist()[:10]}...")
        if '代码' in df.columns:
            print(f"Sample row for 510300:\n{df[df['代码'] == '510300'].to_dict('records')}")
    except Exception as e:
        print(f"ETF Error: {e}")

    print("\n--- Open Fund Daily ---")
    try:
        df = ak.fund_open_fund_daily_em()
        print(f"Columns: {df.columns.tolist()[:10]}...")
        code_col = '基金代码' if '基金代码' in df.columns else '代码'
        if code_col in df.columns:
            print(f"Sample row for 000001:\n{df[df[code_col] == '000001'].to_dict('records')}")
    except Exception as e:
        print(f"Open Fund Error: {e}")

if __name__ == "__main__":
    debug_columns()
