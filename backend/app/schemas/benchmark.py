from pydantic import BaseModel, Field, model_validator


class BenchmarkProfile(BaseModel):
    sport: str = Field(min_length=1)
    movement_phase: str = Field(min_length=1)
    metric_name: str = Field(min_length=1)
    ideal_min: float
    ideal_max: float
    optimal_value: float | None = None
    unit: str = Field(min_length=1)
    research_reference: str | None = None
    notes: str = Field(min_length=1)
    weight: float = Field(gt=0)
    maximum_deviation: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_range(self) -> "BenchmarkProfile":
        if self.ideal_min > self.ideal_max:
            raise ValueError("ideal_min must not exceed ideal_max")
        if self.optimal_value is not None and not (
            self.ideal_min <= self.optimal_value <= self.ideal_max
        ):
            raise ValueError("optimal_value must be within the ideal range")
        return self

    @property
    def target(self) -> float:
        if self.optimal_value is not None:
            return self.optimal_value
        return (self.ideal_min + self.ideal_max) / 2


class MetricDeviation(BaseModel):
    actual: float
    target: float
    signed_deviation: float
    absolute_deviation: float = Field(ge=0)
    deviation_percentage: float | None = Field(default=None, ge=0)
    unit: str


class BilateralMetricDeviation(BaseModel):
    left: MetricDeviation
    right: MetricDeviation


class MetricDeviations(BaseModel):
    knee_angle: BilateralMetricDeviation
    elbow_angle: BilateralMetricDeviation
    hip_angle: BilateralMetricDeviation
    stride_length: MetricDeviation


class PhaseBenchmarkScores(BaseModel):
    movement_phase: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(ge=0)
    frame_count: int = Field(gt=0)
    technique_score: float = Field(ge=0, le=100)
    efficiency_score: float = Field(ge=0, le=100)
    balance_score: float = Field(ge=0, le=100)
    overall_score: float = Field(ge=0, le=100)
    metric_deviations: MetricDeviations


class BenchmarkScores(BaseModel):
    technique_score: float = Field(ge=0, le=100)
    efficiency_score: float = Field(ge=0, le=100)
    balance_score: float = Field(ge=0, le=100)
    overall_score: float | None = Field(default=None, ge=0, le=100)
    metric_deviations: MetricDeviations | None = None
    phase_scores: list[PhaseBenchmarkScores] = Field(default_factory=list)
