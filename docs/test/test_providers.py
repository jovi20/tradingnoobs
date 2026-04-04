import akshare_one
import akshare as ak

# Test A-Shares
try:
    print("Testing A-Share (600519)...")
    a_share_df = ak.stock_individual_info_em(symbol="600519")
    print(f"A-Share Result:\n{a_share_df.head()}")
except Exception as e:
    print(f"A-Share Error: {e}")

# Test HK-Shares
try:
    print("\nTesting HK-Share (00700)...")
    hk_share_df = akshare_one.get_realtime_data(symbol="00700", source="eastmoney_direct")
    print(f"HK-Share Result:\n{hk_share_df.head()}")
except Exception as e:
    print(f"HK-Share Error: {e}")
