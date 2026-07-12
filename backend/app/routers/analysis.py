from fastapi import APIRouter, HTTPException

from app.schemas.jump import JumpAnalysisRequest, JumpAnalysisResult
from app.services.jump_analyzer import AnalysisError, analyze_vertical_jump

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.post("/jump", response_model=JumpAnalysisResult)
def analyze_jump(payload: JumpAnalysisRequest) -> JumpAnalysisResult:
    try:
        return analyze_vertical_jump(payload)
    except AnalysisError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
