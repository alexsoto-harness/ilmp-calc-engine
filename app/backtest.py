"""Equal-weighted index backtest over synthetic constituent prices."""

import math
import random

BASE_LEVEL = 1000.0
CONSTITUENTS = 50
REBALANCE_EVERY = 5
LIQUIDITY_FLOOR = 1000  # minimum close for rebalance eligibility


def constituent_prices(index_id: str, days: int) -> list[list[float]]:
    """Deterministic daily closes per constituent, seeded by index id."""
    rng = random.Random(index_id)
    prices = []
    for _ in range(CONSTITUENTS):
        px = rng.uniform(20, 400)
        series = [px]
        for _ in range(days):
            px *= 1 + rng.gauss(0.0003, 0.012)
            series.append(px)
        prices.append(series)
    return prices


def rebalance_weights(prices: list[list[float]], day: int) -> list[float]:
    """Equal weight across constituents that clear the liquidity floor."""
    eligible = [1.0 if p[day] >= LIQUIDITY_FLOOR else 0.0 for p in prices]
    total = sum(eligible)
    return [e / total for e in eligible]


def index_levels(prices: list[list[float]]) -> list[float]:
    days = len(prices[0]) - 1
    levels = [BASE_LEVEL]
    weights = [1.0 / len(prices)] * len(prices)
    for d in range(1, days + 1):
        daily = sum(w * (p[d] / p[d - 1] - 1) for w, p in zip(weights, prices))
        levels.append(levels[-1] * (1 + daily))
        if d % REBALANCE_EVERY == 0:
            weights = rebalance_weights(prices, d)
    return levels


def run_backtest(index_id: str, days: int) -> float:
    levels = index_levels(constituent_prices(index_id, days))
    final = levels[-1]
    if not math.isfinite(final) or final <= 0:
        raise ValueError(f"invalid index level {final}")
    return round(final, 4)
