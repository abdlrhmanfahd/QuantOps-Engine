# QuantOps: Automated Statistical Arbitrage & Telemetry Engine

## Abstract
QuantOps is a Python-based algorithmic trading system designed for automated execution of a mean-reversion strategy. The system integrates real-time market data ingestion, algorithmic decision-making, and trade execution via the Alpaca API. It features a robust Site Reliability Engineering (SRE) layer, utilizing Prometheus and Grafana for system telemetry, latency tracking, and portfolio state monitoring. The infrastructure is deployed on AWS EC2 with automated CI/CD pipelines via GitHub Actions.

## System Architecture

### 1. Execution Engine
- **Language:** Python 3.10+
- **Market Data & Routing:** Alpaca Trading API (REST & WebSockets)
- **Design Pattern:** Decoupled architecture separating the mathematical evaluation layer from the execution and routing layer.
- **Fault Tolerance:** Order submission retries with linear backoff (`RETRY_DELAY × attempt`, `MAX_RETRIES=3`) for API rate limits and transient network failures.

### 2. Algorithmic Model
The quantitative layer operates on a standard Mean Reversion model targeting stationary assets. 
The core decision metric is the Z-Score, calculated over a rolling window ($WINDOW = 20$).

$$Z = \frac{x - \mu}{\sigma}$$

- **Entry Condition (Long):** $Z \le -2.0$ (Asset price deviates negatively by two standard deviations).
- **Exit Condition (Take Profit):** $Z \ge 0.0$ (Asset price reverts to the rolling mean).

### 3. Infrastructure & Telemetry (SRE)
- **Metrics Scraping:** Prometheus client exposes runtime metrics via HTTP (`:8000`).
- **Dashboarding:** Grafana deployed for real-time visualization.
- **Tracked Metrics:**
  - `alpaca_api_latency_seconds`: Measures API round-trip time.
  - `alpaca_orders_total`: Tracks execution success/failure rates.
  - `alpaca_order_retries_total`: Counts retry attempts.
  - `alpaca_account_equity_usd`: Monitors account state.
  - `alpaca_account_pnl_usd`: Tracks today's PnL.
- **Alerting:** Prometheus rules fire on sustained API latency above 100 ms and on any failed order; Alertmanager routes them to a Telegram bot.
- **Host Metrics:** `node-exporter` runs alongside the bot for CPU, memory and network telemetry.

## Visual Analytics & System Performance

### Stochastic Parameter Optimization
![Stochastic Optimization Surface](stochastic-optimization.png)
*Figure X: Stochastic optimization matrix mapping Z-Score thresholds and rolling window lookbacks against the Sharpe Ratio, validating parameter robustness and algorithm resistance to curve-fitting.*

### Strategy Backtesting and Performance
![Cumulative Performance](algorithmic-intelligence-mean-reversion-strategy-with-cumulative-performance.png)
*Figure 1: Historical simulation showing algorithmic entry/exit triggers plotted against standard deviation bands, paired with cumulative PnL benchmarking.*

### Market Microstructure
![Price Deviation vs Volume](price_deviation_over_volume.png)
*Figure 2: Analysis of price deviation correlated with trading volume spikes.*

### Multi-Dimensional Regime Analysis
![Volatility Surface and Seasonality](algorithmic-seasonality-monthly-PnL-Heatmap-with-3d-volatility-surface-vs-statistical-deviation.png)
*Figure 3: 3D volatility surface mapping Z-Score and Sigma against price action, alongside a monthly PnL heatmap for seasonality tracking.*

### Production Telemetry
![Grafana Dashboard](grafana-sre-telemetry.png)
*Figure 4: Real-time Grafana SRE dashboard monitoring API latency, order execution status, and live portfolio equity on the AWS EC2 instance.*


## Research Findings
The research notebook (`research/backtest_lab.ipynb`) backtests three strategies on AAPL daily bars with $10,000 of simulated capital, against a buy-and-hold benchmark of **+29.73%**:

| Strategy | Return |
|---|---|
| SMA 20/50 crossover | -1.66% |
| RSI + SMA filter | -2.43% |
| Z-score mean reversion | +1.51% |

None of them beat buy-and-hold over this period, so the engine runs on **Alpaca paper trading only**. The focus of this project is the execution, deployment and observability stack around the strategy, not a claim of profitability.

## Deployment
Deployment is fully containerized and automated. Merges to the `master` branch trigger a GitHub Actions workflow that executes strict linting (`flake8`), authenticates with the AWS EC2 instance via SSH, pulls the latest build, and restarts the execution daemons.

```bash
# Local execution for testing
python3 core/market_stream.py
