from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.ai.dialogue_manager import handle_message

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    result = handle_message(
        request.conversation_id,
        request.message,
    )
    return ChatResponse(**result)