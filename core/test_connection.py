import os
from dotenv import load_dotenv
load_dotenv()
from alpaca.trading.client import TradingClient
api_key = os.environ.get('APCA_API_KEY_ID')
secret_key = os.environ.get('APCA_API_SECRET_KEY')

if not api_key or not secret_key:
    print("[ERROR] Security Keys not found in environment!")
    exit(1) 

trading_client = TradingClient(api_key, secret_key, paper=True)

try:
    account = trading_client.get_account()
    print(f"\n[SUCCESS] Connected to Alpaca Quant API")
    print(f"Account Status: {account.status}")
    print(f"Buying Power: ${account.buying_power}")
except Exception as e:
    print(f"\n[FAILED] Connection Error: {e}")
