import os
import sys
import time
import logging
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.common.exceptions import APIError
from prometheus_client import start_http_server, Gauge, Counter

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
load_dotenv()

API_KEY = os.environ.get('APCA_API_KEY_ID')
SECRET_KEY = os.environ.get('APCA_API_SECRET_KEY')
SYMBOL = os.environ.get('TRADE_SYMBOL', 'USDT/USD')
QTY = float(os.environ.get('TRADE_QTY', '10'))
METRICS_PORT = int(os.environ.get('METRICS_PORT', '8000'))
MAX_RETRIES = int(os.environ.get('MAX_RETRIES', '3'))
RETRY_DELAY = float(os.environ.get('RETRY_DELAY', '2'))

if not API_KEY or not SECRET_KEY:
    logging.error("[CONFIG] Missing APCA_API_KEY_ID or APCA_API_SECRET_KEY. Exiting.")
    sys.exit(1)

ALPACA_LATENCY = Gauge('alpaca_api_latency_seconds', 'Alpaca API response latency')
ORDER_STATUS = Counter('alpaca_orders_total', 'Total number of orders', ['status'])
ORDER_RETRIES = Counter('alpaca_order_retries_total', 'Total number of order retry attempts')

ACCOUNT_EQUITY = Gauge('alpaca_account_equity_usd', 'Total account equity in USD')
ACCOUNT_PNL = Gauge('alpaca_account_pnl_usd', 'Today PnL in USD')

trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)

def submit_order_with_retry(client, order_request, max_retries=3, delay=2):
    last_exception = None

    for attempt in range(1, max_retries + 1):
        start_time = time.time()

        try:
            order = client.submit_order(order_data=order_request)
            latency = time.time() - start_time

            ALPACA_LATENCY.set(latency)
            ORDER_STATUS.labels(status='success').inc()

            logging.info(
                f"[SUCCESS] Order {order.id} executed in "
                f"{latency:.4f}s (attempt {attempt})"
            )

            return order

        except APIError as e:
            latency = time.time() - start_time
            ALPACA_LATENCY.set(latency)

            last_exception = e
            logging.error(
                f"[FAILED] Attempt {attempt}/{max_retries} "
                f"- API error: {e}"
            )

            ORDER_RETRIES.inc()

            if attempt < max_retries:
                time.sleep(delay * attempt)

        except Exception as e:
            latency = time.time() - start_time
            ALPACA_LATENCY.set(latency)

            last_exception = e
            logging.error(
                f"[FAILED] Attempt {attempt}/{max_retries} "
                f"- Unexpected error: {e}"
            )

            ORDER_RETRIES.inc()

            if attempt < max_retries:
                time.sleep(delay * attempt)

    ORDER_STATUS.labels(status='failed').inc()

    logging.error(
        f"[FAILED] All {max_retries} attempts failed. "
        f"Last error: {last_exception}"
    )

    return None

def update_financials(client):
    try:
        account = client.get_account()

        equity = float(account.equity)
        last_equity = float(account.last_equity)
        pnl = equity - last_equity

        ACCOUNT_EQUITY.set(equity)
        ACCOUNT_PNL.set(pnl)

        logging.info(
            f"[FINANCE] Equity: ${equity:.2f} | "
            f"Today's PnL: ${pnl:.2f}"
        )

    except Exception as e:
        logging.error(
            f"[FINANCE FAILED] Could not sync account data: {e}"
        )

def main():
    start_http_server(METRICS_PORT, addr='0.0.0.0')

    logging.info(
        f"[SRE] Metrics server active on port "
        f"{METRICS_PORT} (0.0.0.0)"
    )

    market_order = MarketOrderRequest(
        symbol=SYMBOL,
        qty=QTY,
        side=OrderSide.BUY,
        time_in_force=TimeInForce.GTC
    )

    logging.info(
        f"[SYSTEM] Starting continuous execution loop for: {SYMBOL}"
    )

    while True:
        logging.info(
            f"[CYCLE] Submitting order: {SYMBOL}, qty={QTY}"
        )

        submit_order_with_retry(
            trading_client,
            market_order,
            MAX_RETRIES,
            RETRY_DELAY
        )

        update_financials(trading_client)

        time.sleep(60)

if __name__ == "__main__":
    main()
