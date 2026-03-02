from __future__ import annotations

from investment_agent.schemas import FundamentalsSnapshot, StrategyResult


class QualityStrategy:
    name = "quality"

    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
        return max(lo, min(hi, value))

    def evaluate(self, fundamentals: FundamentalsSnapshot | None) -> StrategyResult:
        if fundamentals is None:
            return StrategyResult(
                name=self.name,
                score=0.0,
                explanation="No fundamentals data available.",
                factors={},
                notes=["Fundamentals data missing"],
            )

        partial_scores: list[float] = []
        factor_scores: dict[str, float] = {}
        notes: list[str] = []

        rg = fundamentals.revenue_growth_yoy
        if rg is not None:
            score = self._clamp((rg + 10.0) * 2.5)
            partial_scores.append(score)
            factor_scores["revenue_growth"] = round(score, 2)

        gm = fundamentals.gross_margin
        if gm is not None:
            score = self._clamp(gm * 120.0)
            partial_scores.append(score)
            factor_scores["gross_margin"] = round(score, 2)

        om = fundamentals.operating_margin
        if om is not None:
            score = self._clamp((om + 0.05) * 200.0)
            partial_scores.append(score)
            factor_scores["operating_margin"] = round(score, 2)

        dte = fundamentals.debt_to_equity
        if dte is not None:
            score = self._clamp(100.0 - (dte * 30.0))
            partial_scores.append(score)
            factor_scores["leverage"] = round(score, 2)

        roic = fundamentals.roic
        if roic is not None:
            score = self._clamp((roic + 0.05) * 250.0)
            partial_scores.append(score)
            factor_scores["roic"] = round(score, 2)

        pe = fundamentals.pe_ratio
        if pe is not None:
            if pe <= 0:
                partial_scores.append(20.0)
                factor_scores["valuation"] = 20.0
                notes.append("Negative or zero PE reduces quality score.")
            else:
                # Penalize extreme valuation while allowing quality growth names.
                score = self._clamp(100.0 - abs(pe - 22.0) * 2.2)
                partial_scores.append(score)
                factor_scores["valuation"] = round(score, 2)
                if pe > 35:
                    notes.append("High valuation slightly reduces risk-adjusted score.")

        if not partial_scores:
            return StrategyResult(
                name=self.name,
                score=0.0,
                explanation="Fundamentals present but missing scoreable fields.",
                factors={},
                notes=["No fundamentals fields were scoreable."],
            )

        score = round(sum(partial_scores) / len(partial_scores), 2)
        explanation = (
            f"Quality score {score:.2f}/100 from profitability, growth, leverage, and valuation checks "
            f"across {len(partial_scores)} available signals."
        )
        return StrategyResult(
            name=self.name,
            score=score,
            explanation=explanation,
            factors=factor_scores,
            notes=notes,
        )
