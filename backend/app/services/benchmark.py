from app.schemas.benchmark import (
    BenchmarkProfile,
    BenchmarkScores,
    BilateralMetricDeviation,
    MetricDeviation,
    MetricDeviations,
)
from app.schemas.biomechanics import BiomechanicalMetrics, BilateralAngleMetric


class BenchmarkEngine:
    def __init__(self, profiles: list[BenchmarkProfile]):
        self.profiles = {profile.metric_name: profile for profile in profiles}
        required = {
            "knee_angle",
            "elbow_angle",
            "hip_angle",
            "stride_length",
            "symmetry_difference",
        }
        missing = required - self.profiles.keys()
        if missing:
            raise ValueError(
                f"Missing benchmark profiles: {', '.join(sorted(missing))}"
            )

    def compare(self, metrics: BiomechanicalMetrics) -> BenchmarkScores:
        technique_score = self._technique_score(metrics)
        balance_score = self._balance_score(metrics)
        stride_score = self._profile_similarity(
            metrics.stride_length.value,
            self._profile("stride_length"),
        )
        efficiency_score = (
            stride_score * 0.60
            + technique_score * 0.25
            + balance_score * 0.15
        )
        if metrics.running is not None:
            running_technique = self._running_technique_score(metrics)
            running_efficiency = self._running_efficiency_score(metrics)
            running_balance = self._running_balance_score(metrics)
            if running_technique is not None:
                technique_score = technique_score * 0.55 + running_technique * 0.45
            if running_efficiency is not None:
                efficiency_score = efficiency_score * 0.25 + running_efficiency * 0.75
            if running_balance is not None:
                balance_score = balance_score * 0.50 + running_balance * 0.50

        overall_score = (
            technique_score * 0.40
            + efficiency_score * 0.35
            + balance_score * 0.25
        )

        return BenchmarkScores(
            technique_score=round(technique_score, 2),
            efficiency_score=round(efficiency_score, 2),
            balance_score=round(balance_score, 2),
            overall_score=round(overall_score, 2),
            metric_deviations=self._metric_deviations(metrics),
        )

    def compare_json(self, metrics: BiomechanicalMetrics) -> dict:
        return self.compare(metrics).model_dump(mode="json")

    def _technique_score(self, metrics: BiomechanicalMetrics) -> float:
        comparisons = (
            (metrics.knee_angle, self._profile("knee_angle")),
            (metrics.elbow_angle, self._profile("elbow_angle")),
            (metrics.hip_angle, self._profile("hip_angle")),
        )
        weighted_scores = [
            (self._profile_similarity(angle, profile), profile.weight)
            for bilateral, profile in comparisons
            for angle in (bilateral.left, bilateral.right)
        ]
        return self._weighted_average(weighted_scores)

    def _balance_score(self, metrics: BiomechanicalMetrics) -> float:
        angles: tuple[tuple[BilateralAngleMetric, BenchmarkProfile], ...] = (
            (metrics.knee_angle, self._profile("knee_angle")),
            (metrics.elbow_angle, self._profile("elbow_angle")),
            (metrics.hip_angle, self._profile("hip_angle")),
        )
        symmetry_profile = self._profile("symmetry_difference")
        weighted_scores = [
            (
                self._profile_similarity(
                    abs(angle.left - angle.right), symmetry_profile
                ),
                profile.weight,
            )
            for angle, profile in angles
        ]
        return self._weighted_average(weighted_scores)

    def _running_technique_score(self, metrics: BiomechanicalMetrics) -> float | None:
        running = metrics.running
        if running is None:
            return None
        return self._available_weighted_average(
            [
                ("running_overstriding_index_pct", running.overstriding_index_pct),
                ("running_cadence_spm", running.cadence_spm),
                ("running_stride_length_norm", running.stride_length_norm),
            ]
        )

    def _running_efficiency_score(self, metrics: BiomechanicalMetrics) -> float | None:
        running = metrics.running
        if running is None:
            return None
        return self._available_weighted_average(
            [
                ("running_stride_length_norm", running.stride_length_norm),
                ("running_contact_time_ms", running.contact_time_ms),
                ("running_duty_factor_pct", running.duty_factor_pct),
                (
                    "running_vertical_oscillation_ratio_pct",
                    running.vertical_oscillation_ratio_pct,
                ),
            ]
        )

    def _running_balance_score(self, metrics: BiomechanicalMetrics) -> float | None:
        running = metrics.running
        if running is None:
            return None
        return self._available_weighted_average(
            [
                ("running_stride_time_symmetry_pct", running.stride_time_symmetry_pct),
                (
                    "running_contact_time_symmetry_pct",
                    running.contact_time_symmetry_pct,
                ),
            ]
        )

    def _available_weighted_average(
        self, values: list[tuple[str, float | None]]
    ) -> float | None:
        scored = [
            (
                self._profile_similarity(value, self._profile(metric_name)),
                self._profile(metric_name).weight,
            )
            for metric_name, value in values
            if value is not None and metric_name in self.profiles
        ]
        if not scored:
            return None
        return self._weighted_average(scored)

    def _metric_deviations(
        self, metrics: BiomechanicalMetrics
    ) -> MetricDeviations:
        return MetricDeviations(
            knee_angle=self._bilateral_deviation(
                metrics.knee_angle, self._profile("knee_angle")
            ),
            elbow_angle=self._bilateral_deviation(
                metrics.elbow_angle, self._profile("elbow_angle")
            ),
            hip_angle=self._bilateral_deviation(
                metrics.hip_angle, self._profile("hip_angle")
            ),
            stride_length=self._deviation(
                metrics.stride_length.value,
                self._profile("stride_length").target,
                metrics.stride_length.unit,
            ),
        )

    @classmethod
    def _bilateral_deviation(
        cls, metric: BilateralAngleMetric, profile: BenchmarkProfile
    ) -> BilateralMetricDeviation:
        return BilateralMetricDeviation(
            left=cls._deviation(metric.left, profile.target, metric.unit),
            right=cls._deviation(metric.right, profile.target, metric.unit),
        )

    def _profile(self, metric_name: str) -> BenchmarkProfile:
        return self.profiles[metric_name]

    @staticmethod
    def _weighted_average(values: list[tuple[float, float]]) -> float:
        total_weight = sum(weight for _, weight in values)
        return sum(value * weight for value, weight in values) / total_weight

    @classmethod
    def _profile_similarity(
        cls, value: float, profile: BenchmarkProfile
    ) -> float:
        if profile.ideal_min <= value <= profile.ideal_max:
            return 100.0
        nearest = (
            profile.ideal_min if value < profile.ideal_min else profile.ideal_max
        )
        return cls._similarity(value, nearest, profile.maximum_deviation)

    @staticmethod
    def _deviation(value: float, target: float, unit: str) -> MetricDeviation:
        signed_deviation = value - target
        percentage = (
            abs(signed_deviation) / abs(target) * 100 if target != 0 else None
        )
        return MetricDeviation(
            actual=round(value, 4),
            target=round(target, 4),
            signed_deviation=round(signed_deviation, 4),
            absolute_deviation=round(abs(signed_deviation), 4),
            deviation_percentage=(
                round(percentage, 2) if percentage is not None else None
            ),
            unit=unit,
        )

    @staticmethod
    def _similarity(value: float, target: float, max_deviation: float) -> float:
        deviation = abs(value - target)
        return max(0.0, 100.0 * (1.0 - deviation / max_deviation))
