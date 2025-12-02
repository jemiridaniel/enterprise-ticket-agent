from fastapi import APIRouter
from ..services.llm_service import call_llm

router = APIRouter()

@router.get("/test-llm")
async def test_llm():
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Say one short sentence about Mac M2."}
    ]
    answer = await call_llm(messages)
    return {"answer": answer}
