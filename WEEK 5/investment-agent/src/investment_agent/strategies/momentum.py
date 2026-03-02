from __future__ import annotations

from investment_agent.schemas import MarketDataSnapshot, StrategyResult


class MomentumStrategy:
    name = "momentum"

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    def evaluate(self, market_data: MarketDataSnapshot | None) -> StrategyResult:
        if market_data is None:
            return StrategyResult(
                name=self.name,
                score=0.0,
                explanation="No market data available.",
                factors={},
                notes=["Market data missing"],
            )

        weighted_points = 0.0
        weighted_total = 0.0
        factors: dict[str, float] = {}
        notes: list[str] = []

        def add_return_component(
            key: str, value: float | None, weight: float, scale: float = 2.0
        ) -> None:
            nonlocal weighted_points, weighted_total
            if value is None:
                return
            component = self._clamp(50.0 + (value * scale))
            weighted_points += component * weight
            weighted_total += weight
            factors[key] = round(component, 2)

        add_return_component("return_1m", market_data.return_1m, weight=1.0)
        add_return_component("return_3m", market_data.return_3m, weight=1.5)
        add_return_component("return_6m", market_data.return_6m, weight=1.0)
        add_return_component("return_12m", market_data.return_12m, weight=0.5, scale=1.2)

        if market_data.change_pct_1d is not None:
            day_component = self._clamp(50.0 + market_data.change_pct_1d)
            weighted_points += day_component * 0.5
            weighted_total += 0.5
            factors["return_1d"] = round(day_component, 2)

        if weighted_total == 0:
            return StrategyResult(
                name=self.name,
                score=0.0,
                explanation="Market data present but missing return signals.",
                factors=factors,
                notes=["No momentum return fields were scoreable."],
            )

        base_score = weighted_points / weighted_total
        volatility = market_data.volatility_30d
        if volatility is not None:
            # Above ~35% annualized starts to reduce trend confidence.
            penalty = max(0.0, (volatility - 35.0) * 0.6)
            base_score -= penalty
            factors["volatility_penalty"] = round(-penalty, 2)
            if penalty > 0:
                notes.append("High short-term volatility reduces momentum conviction.")
        else:
            factors["volatility_penalty"] = 0.0

        score = round(self._clamp(base_score), 2)
        explanation = (
            f"Momentum score {score:.2f}/100 from multi-horizon returns with a volatility adjustment "
            f"({weighted_total:.1f} weighted factors)."
        )
        return StrategyResult(
            name=self.name,
            score=score,
            explanation=explanation,
            factors=factors,
            notes=notes,
        )
