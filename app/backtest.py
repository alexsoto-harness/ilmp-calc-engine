"""Equal-weighted index backtest over synthetic constituent prices."""

import math
import random

BASE_LEVEL = 1000.0
CONSTITUENTS = 50


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


def index_levels(prices: list[list[float]]) -> list[float]:
    days = len(prices[0]) - 1
    levels = [BASE_LEVEL]
    for d in range(1, days + 1):
        daily = sum(p[d] / p[d - 1] - 1 for p in prices) / len(prices)
        levels.append(levels[-1] * (1 + daily))
    return levels


def run_backtest(index_id: str, days: int) -> float:
    levels = index_levels(constituent_prices(index_id, days))
    final = levels[-1]
    if not math.isfinite(final) or final <= 0:
        raise ValueError(f"invalid index level {final}")
    return round(final, 4)
