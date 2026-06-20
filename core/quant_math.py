import pandas as pd

historical_prices = []
WINDOW = 20

def analyze_tick(current_price):
    global historical_prices

    historical_prices.append(current_price)

    if len(historical_prices) < WINDOW:
        return 0

    if len(historical_prices) > WINDOW:
        historical_prices.pop(0)

    series = pd.Series(historical_prices)

    mu = series.mean()
    sigma = series.std()

    if sigma == 0:
        return 0

    z_score = (current_price - mu) / sigma

    print(
        f"[Math Engine] Price: ${current_price:.2f} | "
        f"Z-Score: {z_score:.2f}"
    )

    if z_score <= -2.0:
        return 1
    elif z_score >= 0:
        return -1
    else:
        return 0