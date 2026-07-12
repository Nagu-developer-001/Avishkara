from app.schemas.benchmark import BenchmarkScores
from app.services.recommendation import RecommendationEngine


def test_generates_strengths_for_high_scores() -> None:
    result = RecommendationEngine().generate(
        BenchmarkScores(
            technique_score=90,
            balance_score=85,
            efficiency_score=82,
        )
    )

    assert len(result.strengths) == 3
    assert result.weaknesses == []
    assert result.improvement_suggestions == []


def test_generates_weaknesses_and_suggestions_for_low_scores() -> None:
    result = RecommendationEngine().generate(
        BenchmarkScores(
            technique_score=45,
            balance_score=50,
            efficiency_score=55,
        )
    )

    assert len(result.weaknesses) == 3
    assert len(result.improvement_suggestions) == 3
    assert result.strengths == []


def test_neutral_scores_do_not_generate_content() -> None:
    result = RecommendationEngine().generate_json(
        BenchmarkScores(
            technique_score=60,
            balance_score=79.99,
            efficiency_score=70,
        )
    )

    assert result == {
        "strengths": [],
        "weaknesses": [],
        "improvement_suggestions": [],
    }


def test_thresholds_are_inclusive_for_strengths_only() -> None:
    result = RecommendationEngine().generate(
        BenchmarkScores(
            technique_score=80,
            balance_score=60,
            efficiency_score=59.99,
        )
    )

    assert len(result.strengths) == 1
    assert len(result.weaknesses) == 1
    assert len(result.improvement_suggestions) == 1
