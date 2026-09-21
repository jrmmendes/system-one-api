from fastapi import APIRouter

from app.models import ClassifyRequest, ClassifyResponse
from app.services.laya_service import get_laya_service

router = APIRouter()


@router.post("/classify", response_model=ClassifyResponse)
async def classify(body: ClassifyRequest) -> ClassifyResponse:
    service = get_laya_service()

    raw_questions = {k: v.model_dump(exclude_none=True) for k, v in body.questions.items()}
    result = service.predict(text=body.text, questions=raw_questions)

    return ClassifyResponse(
        model=result["model"],
        answers=result["answers"],
        usage=result["usage"],
        routing=result.get("routing"),
    )
