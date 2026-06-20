import os
import sys
import time
import logging
from dotenv import load_dotenv
from quant_math import analyze_tick
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.common.exceptions import APIError

from prometheus_client import (
    start_http_server,
    Gauge,
    Counter,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

load_dotenv()

API_KEY = os.environ.get("APCA_API_KEY_ID")
SECRET_KEY = os.environ.get("APCA_API_SECRET_KEY")

SYMBOL = os.environ.get("TRADE_SYMBOL", "AAPL")
QTY = float(os.environ.get("TRADE_QTY", "1"))

METRICS_PORT = int(os.environ.get("METRICS_PORT", "8000"))

MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.environ.get("RETRY_DELAY", "2"))

if not API_KEY or not SECRET_KEY:
    logging.error(
        "[CONFIG] Missing APCA_API_KEY_ID "
        "or APCA_API_SECRET_KEY. Exiting."
    )
    sys.exit(1)

ALPACA_LATENCY = Gauge(
    "alpaca_api_latency_seconds",
    "Alpaca API response latency",
)

ORDER_STATUS = Counter(
    "alpaca_orders_total",
    "Total number of orders",
    ["status"],
)

ORDER_RETRIES = Counter(
    "alpaca_order_retries_total",
    "Total number of order retry attempts",
)

ACCOUNT_EQUITY = Gauge(
    "alpaca_account_equity_usd",
    "Total account equity in USD",
)

ACCOUNT_PNL = Gauge(
    "alpaca_account_pnl_usd",
    "Today PnL in USD",
)

trading_client = TradingClient(
    API_KEY,
    SECRET_KEY,
    paper=True,
)

data_client = StockHistoricalDataClient(
    API_KEY,
    SECRET_KEY,
)

def submit_order_with_retry(
    client,
    order_request,
    max_retries=3,
    delay=2,
):
    last_exception = None

    for attempt in range(1, max_retries + 1):
        start_time = time.time()

        try:
            order = client.submit_order(
                order_data=order_request
            )

            latency = time.time() - start_time

            ALPACA_LATENCY.set(latency)

            ORDER_STATUS.labels(
                status="success"
            ).inc()

            logging.info(
                f"[SUCCESS] Order {order.id} "
                f"executed in {latency:.4f}s "
                f"(attempt {attempt})"
            )

            return order

        except APIError as e:
            latency = time.time() - start_time

            ALPACA_LATENCY.set(latency)

            last_exception = e

            logging.error(
                f"[FAILED] Attempt "
                f"{attempt}/{max_retries} "
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
                f"[FAILED] Attempt "
                f"{attempt}/{max_retries} "
                f"- Unexpected error: {e}"
            )

            ORDER_RETRIES.inc()

            if attempt < max_retries:
                time.sleep(delay * attempt)

    ORDER_STATUS.labels(
        status="failed"
    ).inc()

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
            f"[FINANCE FAILED] "
            f"Could not sync account data: {e}"
        )

def main():
    start_http_server(
        METRICS_PORT,
        addr="0.0.0.0",
    )

    logging.info(
        f"[SRE] Metrics server active "
        f"on port {METRICS_PORT} (0.0.0.0)"
    )

    logging.info(
        f"[SYSTEM] Starting autonomous "
        f"quant loop for: {SYMBOL}"
    )

    shares_held = 0

    while True:
        try:
            request = StockLatestQuoteRequest(
                symbol_or_symbols=SYMBOL
            )

            quote = data_client.get_stock_latest_quote(
                request
            )

            live_price = float(
                quote[SYMBOL].ask_price
            )

            logging.info(
                f"[MARKET] Live Ask Price "
                f"for {SYMBOL}: "
                f"${live_price:.2f}"
            )

            signal = analyze_tick(
                live_price
            )

            if signal == 1 and shares_held == 0:
                logging.info(
                    "[BRAIN] Z-Score <= -2. "
                    "BUY Signal! Executing..."
                )

                order_request = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=QTY,
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.GTC,
                )

                if submit_order_with_retry(
                    trading_client,
                    order_request,
                    MAX_RETRIES,
                    RETRY_DELAY,
                ):
                    shares_held += QTY

            elif signal == -1 and shares_held > 0:
                logging.info(
                    "[BRAIN] Z-Score >= 0. "
                    "SELL Signal! Taking Profits..."
                )

                order_request = MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=shares_held,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.GTC,
                )

                if submit_order_with_retry(
                    trading_client,
                    order_request,
                    MAX_RETRIES,
                    RETRY_DELAY,
                ):
                    shares_held = 0

            else:
                logging.info(
                    "[BRAIN] No actionable edge "
                    "or conditions not met. "
                    "Waiting..."
                )

        except Exception as e:
            logging.error(
                f"[SYSTEM LOOP ERROR] "
                f"Failed to process tick: {e}"
            )

        update_financials(
            trading_client
        )

        time.sleep(60)

if __name__ == "__main__":
    main()