from dataclasses import dataclass


@dataclass(frozen=True)
class RecommendationCandidate:
    sku: str
    shortage_ratio: float
    sales_velocity: float
    margin_ratio: float
    supplier_availability: float


class RecommendationService:
    def rank(self, candidates: list[RecommendationCandidate]) -> list[dict]:
        ranked = []
        for item in candidates:
            score = (
                0.45 * max(0.0, min(item.shortage_ratio, 1.0))
                + 0.25 * max(0.0, min(item.sales_velocity, 1.0))
                + 0.15 * max(0.0, min(item.margin_ratio, 1.0))
                + 0.15 * max(0.0, min(item.supplier_availability, 1.0))
            )
            ranked.append({"sku": item.sku, "score": round(score, 6)})
        return sorted(ranked, key=lambda item: (-item["score"], item["sku"]))
