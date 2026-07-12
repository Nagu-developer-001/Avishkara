import json
from pathlib import Path

import pytest

from app.services.benchmark_loader import (
    BenchmarkProfileError,
    BenchmarkProfileLoader,
    load_benchmark,
)


def test_loads_the_selected_sport_file() -> None:
    running = BenchmarkProfileLoader().load("Running")
    jumping = BenchmarkProfileLoader().load("Jumping")
    bowling = BenchmarkProfileLoader().load("Bowling")

    assert {profile.sport for profile in running} == {"Running"}
    assert {profile.sport for profile in jumping} == {"Jumping"}
    assert {profile.sport for profile in bowling} == {"Bowling"}
    assert {profile.movement_phase for profile in running} == {"Foot Strike"}
    assert {profile.movement_phase for profile in jumping} == {"Preparation"}
    assert {profile.movement_phase for profile in bowling} == {"Run Up"}
    assert all(profile.research_reference is None for profile in running)
    assert all(profile.notes for profile in running)
    assert running[0].optimal_value == running[0].target


def test_loads_an_explicit_phase_without_changing_the_engine_contract() -> None:
    profiles = load_benchmark(sport="Running", phase="Toe Off")

    assert len(profiles) == 5
    assert {profile.movement_phase for profile in profiles} == {"Toe Off"}
    assert {profile.metric_name for profile in profiles} == {
        "knee_angle",
        "elbow_angle",
        "hip_angle",
        "stride_length",
        "symmetry_difference",
    }


@pytest.mark.parametrize(
    ("sport", "phases"),
    [
        ("Running", ["Foot Strike", "Mid Stance", "Toe Off"]),
        ("Jumping", ["Preparation", "Take Off", "Flight", "Landing"]),
        (
            "Bowling",
            [
                "Run Up",
                "Back Foot Contact",
                "Front Foot Contact",
                "Ball Release",
                "Follow Through",
            ],
        ),
    ],
)
def test_all_configured_phases_can_be_selected(
    sport: str, phases: list[str]
) -> None:
    for phase in phases:
        selected = load_benchmark(sport=sport, phase=phase)
        assert len(selected) >= 5
        assert {profile.movement_phase for profile in selected} == {phase}


def test_running_foot_strike_contains_stride_quality_profiles() -> None:
    profiles = load_benchmark(sport="Running", phase="Foot Strike")

    assert {
        "running_stride_length_norm",
        "running_cadence_spm",
        "running_contact_time_ms",
        "running_overstriding_index_pct",
        "running_stride_time_symmetry_pct",
    }.issubset({profile.metric_name for profile in profiles})


def test_values_are_loaded_from_json(tmp_path: Path) -> None:
    source = Path(__file__).resolve().parents[1] / "benchmarks" / "running.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload[0]["ideal_min"] = 72
    payload[0]["ideal_max"] = 84
    payload[0]["optimal_value"] = 78
    (tmp_path / "running.json").write_text(json.dumps(payload), encoding="utf-8")

    profiles = BenchmarkProfileLoader(tmp_path).load("Running")

    assert profiles[0].ideal_min == 72
    assert profiles[0].ideal_max == 84
    assert profiles[0].optimal_value == 78
    assert profiles[0].target == 78


def test_rejects_an_unknown_sport() -> None:
    with pytest.raises(BenchmarkProfileError, match="No benchmark file"):
        BenchmarkProfileLoader().load("Swimming")


def test_rejects_an_unknown_phase() -> None:
    with pytest.raises(BenchmarkProfileError, match="No benchmark phase"):
        load_benchmark(sport="Running", phase="Flight")


def test_rejects_invalid_profile_json(tmp_path: Path) -> None:
    (tmp_path / "running.json").write_text("[]", encoding="utf-8")

    with pytest.raises(BenchmarkProfileError, match="empty"):
        BenchmarkProfileLoader(tmp_path).load("Running")


def test_rejects_an_optimal_value_outside_the_ideal_range(
    tmp_path: Path,
) -> None:
    source = Path(__file__).resolve().parents[1] / "benchmarks" / "running.json"
    payload = json.loads(source.read_text(encoding="utf-8"))
    payload[0]["optimal_value"] = payload[0]["ideal_max"] + 1
    (tmp_path / "running.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(BenchmarkProfileError, match="Invalid benchmark file"):
        BenchmarkProfileLoader(tmp_path).load("Running")
