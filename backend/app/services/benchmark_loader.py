import json
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from app.schemas.benchmark import BenchmarkProfile

BENCHMARK_DIRECTORY = Path(__file__).resolve().parents[2] / "benchmarks"
SPORT_FILES = {
    "Running": "running.json",
    "Jumping": "jumping.json",
    "Bowling": "cricket_bowling.json",
}


class BenchmarkProfileError(ValueError):
    pass


class BenchmarkProfileLoader:
    def __init__(self, directory: Path = BENCHMARK_DIRECTORY):
        self.directory = directory

    def load(
        self, sport: str, phase: str | None = None
    ) -> list[BenchmarkProfile]:
        filename = SPORT_FILES.get(sport)
        if filename is None:
            raise BenchmarkProfileError(f"No benchmark file configured for {sport}")

        path = self.directory / filename
        if not path.is_file():
            raise BenchmarkProfileError(f"Benchmark file does not exist: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            profiles = TypeAdapter(list[BenchmarkProfile]).validate_python(payload)
        except (json.JSONDecodeError, ValidationError) as exc:
            raise BenchmarkProfileError(f"Invalid benchmark file: {path}") from exc
        if not profiles:
            raise BenchmarkProfileError(f"Benchmark file is empty: {path}")
        if any(profile.sport != sport for profile in profiles):
            raise BenchmarkProfileError(
                f"Benchmark file contains a profile for a different sport: {path}"
            )
        phases = list(dict.fromkeys(profile.movement_phase for profile in profiles))
        selected_phase = phase or phases[0]
        selected = [
            profile
            for profile in profiles
            if profile.movement_phase == selected_phase
        ]
        if not selected:
            raise BenchmarkProfileError(
                f"No benchmark phase '{selected_phase}' configured for {sport}"
            )
        return selected


def load_benchmark(
    sport: str,
    phase: str | None = None,
    *,
    directory: Path = BENCHMARK_DIRECTORY,
) -> list[BenchmarkProfile]:
    return BenchmarkProfileLoader(directory).load(sport, phase)
