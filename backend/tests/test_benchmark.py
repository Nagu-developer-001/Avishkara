from app.schemas.biomechanics import (
    BilateralAngleMetric,
    BiomechanicalMetrics,
    DistanceMetric,
    RunningBiomechanicsMetrics,
)
from app.services.benchmark import BenchmarkEngine
from app.services.benchmark_loader import load_benchmark


def benchmark_engine() -> BenchmarkEngine:
    return BenchmarkEngine(load_benchmark("Running"))


def metrics(
    *,
    knee: tuple[float, float] = (90, 90),
    elbow: tuple[float, float] = (90, 90),
    hip: tuple[float, float] = (180, 180),
    stride: float = 0.4,
) -> BiomechanicalMetrics:
    return BiomechanicalMetrics(
        frame_index=1,
        timestamp_ms=33,
        knee_angle=BilateralAngleMetric(left=knee[0], right=knee[1]),
        elbow_angle=BilateralAngleMetric(left=elbow[0], right=elbow[1]),
        hip_angle=BilateralAngleMetric(left=hip[0], right=hip[1]),
        stride_length=DistanceMetric(
            value=stride,
            unit="normalized_image_width",
        ),
    )


def running_metrics(
    *,
    stride_length_norm: float,
    cadence_spm: float,
    contact_time_ms: float,
    duty_factor_pct: float,
    vertical_oscillation_ratio_pct: float,
    overstriding_index_pct: float,
    stride_time_symmetry_pct: float,
    contact_time_symmetry_pct: float,
) -> BiomechanicalMetrics:
    result = metrics()
    result.running = RunningBiomechanicsMetrics(
        stride_length_norm=stride_length_norm,
        cadence_spm=cadence_spm,
        contact_time_ms=contact_time_ms,
        duty_factor_pct=duty_factor_pct,
        vertical_oscillation_ratio_pct=vertical_oscillation_ratio_pct,
        overstriding_index_pct=overstriding_index_pct,
        stride_time_symmetry_pct=stride_time_symmetry_pct,
        contact_time_symmetry_pct=contact_time_symmetry_pct,
    )
    return result


def test_perfect_benchmark_match_scores_100() -> None:
    scores = benchmark_engine().compare(metrics())

    assert scores.technique_score == 100
    assert scores.balance_score == 100
    assert scores.efficiency_score == 100
    assert scores.overall_score == 100
    assert scores.metric_deviations.knee_angle.left.absolute_deviation == 0


def test_scores_asymmetry_and_target_deviation() -> None:
    scores = benchmark_engine().compare(
        metrics(knee=(90, 120), hip=(180, 150), stride=0.2)
    )

    assert scores.technique_score == 88.89
    assert scores.balance_score == 33.33
    assert scores.efficiency_score == 57.22
    assert scores.overall_score == 63.92


def test_returns_signed_and_percentage_metric_deviations() -> None:
    scores = benchmark_engine().compare(metrics(knee=(75, 105), stride=0.5))

    deviations = scores.metric_deviations
    assert deviations.knee_angle.left.signed_deviation == -15
    assert deviations.knee_angle.right.signed_deviation == 15
    assert deviations.knee_angle.left.deviation_percentage == 16.67
    assert deviations.stride_length.signed_deviation == 0.1
    assert deviations.stride_length.deviation_percentage == 25


def test_returns_requested_scores_and_deviations_without_recommendations() -> None:
    result = benchmark_engine().compare_json(metrics(stride=2))

    assert result["technique_score"] == 100
    assert result["efficiency_score"] == 40
    assert result["balance_score"] == 100
    assert result["overall_score"] == 79
    assert result["metric_deviations"]["stride_length"] == {
        "actual": 2.0,
        "target": 0.4,
        "signed_deviation": 1.6,
        "absolute_deviation": 1.6,
        "deviation_percentage": 400.0,
        "unit": "normalized_image_width",
    }
    assert "recommendations" not in result


def test_running_stride_quality_affects_scores() -> None:
    good_scores = benchmark_engine().compare(
        running_metrics(
            stride_length_norm=2.2,
            cadence_spm=178,
            contact_time_ms=185,
            duty_factor_pct=35,
            vertical_oscillation_ratio_pct=6,
            overstriding_index_pct=2.5,
            stride_time_symmetry_pct=1,
            contact_time_symmetry_pct=1,
        )
    )
    poor_scores = benchmark_engine().compare(
        running_metrics(
            stride_length_norm=0.4,
            cadence_spm=120,
            contact_time_ms=360,
            duty_factor_pct=65,
            vertical_oscillation_ratio_pct=24,
            overstriding_index_pct=28,
            stride_time_symmetry_pct=22,
            contact_time_symmetry_pct=20,
        )
    )

    assert good_scores.overall_score > poor_scores.overall_score
    assert good_scores.efficiency_score > poor_scores.efficiency_score
    assert good_scores.balance_score > poor_scores.balance_score
    assert poor_scores.overall_score < 75
