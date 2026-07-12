from dataclasses import dataclass

from app.schemas.benchmark import BenchmarkScores
from app.schemas.recommendation import RecommendationResult

STRENGTH_THRESHOLD = 80
WEAKNESS_THRESHOLD = 60


@dataclass(frozen=True)
class RecommendationRule:
    score_field: str
    strength: str
    weakness: str
    suggestion: str


RULES = (
    RecommendationRule(
        score_field="technique_score",
        strength="Joint movement closely matches the selected technique benchmark.",
        weakness="Joint movement differs significantly from the selected technique benchmark.",
        suggestion="Practise the movement slowly while maintaining the benchmark joint positions.",
    ),
    RecommendationRule(
        score_field="balance_score",
        strength="Left and right joint movements show strong symmetry.",
        weakness="Left and right joint movements show notable asymmetry.",
        suggestion="Use controlled bilateral drills to improve left-right movement symmetry.",
    ),
    RecommendationRule(
        score_field="efficiency_score",
        strength="Movement and stride measurements align efficiently with the benchmark.",
        weakness="Movement and stride measurements show reduced benchmark efficiency.",
        suggestion="Repeat the movement at a controlled pace and reduce unnecessary motion.",
    ),
)


class RecommendationEngine:
    def generate(self, scores: BenchmarkScores) -> RecommendationResult:
        strengths: list[str] = []
        weaknesses: list[str] = []
        suggestions: list[str] = []

        for rule in RULES:
            score = getattr(scores, rule.score_field)
            if score >= STRENGTH_THRESHOLD:
                strengths.append(rule.strength)
            elif score < WEAKNESS_THRESHOLD:
                weaknesses.append(rule.weakness)
                suggestions.append(rule.suggestion)

        return RecommendationResult(
            strengths=strengths,
            weaknesses=weaknesses,
            improvement_suggestions=suggestions,
        )

    def generate_json(self, scores: BenchmarkScores) -> dict:
        return self.generate(scores).model_dump(mode="json")
