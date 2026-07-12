from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def _point(x: float, y: float) -> dict[str, float]:
    return {"x": x, "y": y, "visibility": 0.98}


def _frame(index: int, airborne: bool) -> dict:
    lift = 0.10 if airborne else 0
    return {
        "frame_index": index,
        "landmarks": {
            "left_shoulder": _point(0.46, 0.28 - lift),
            "right_shoulder": _point(0.54, 0.28 - lift),
            "left_hip": _point(0.47, 0.50 - lift),
            "right_hip": _point(0.53, 0.50 - lift),
            "left_knee": _point(0.47, 0.68 - lift),
            "right_knee": _point(0.53, 0.68 - lift),
            "left_ankle": _point(0.47, 0.88 - lift),
            "right_ankle": _point(0.53, 0.88 - lift),
        },
    }


def test_health() -> None:
    response = client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "Avishkara API",
    }
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_vertical_jump_analysis() -> None:
    frames = [_frame(i, airborne=8 <= i < 22) for i in range(30)]
    response = client.post(
        "/api/v1/analysis/jump",
        json={"fps": 30, "athlete_height_m": 1.72, "frames": frames},
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["takeoff_frame"] == 8
    assert result["landing_frame"] == 22
    assert 0.2 < result["metrics"]["jump_height"]["value"] < 0.4
    assert 0 <= result["biomechanics_score"] <= 100
    assert result["metrics"]["jump_height"]["method"].startswith("h =")


def test_rejects_incomplete_pose() -> None:
    frames = [_frame(i, airborne=4 <= i < 9) for i in range(12)]
    del frames[5]["landmarks"]["left_ankle"]
    response = client.post(
        "/api/v1/analysis/jump",
        json={"fps": 30, "athlete_height_m": 1.72, "frames": frames},
    )
    assert response.status_code == 422
    assert "left_ankle" in response.json()["detail"]
