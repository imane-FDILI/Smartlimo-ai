"""
SmartLimo AI - Router du chatbot

Expose une seule route POST /chat/ qui sert de point d'entrée unique entre
le frontend et le gestionnaire de dialogue (dialogue_manager.handle_message).
Ce router reste volontairement très fin : toute la logique métier vit dans
dialogue_manager, ici on ne fait que valider la requête/réponse HTTP.
"""

from fastapi import APIRouter

from app.schemas import ChatRequest, ChatResponse
from app.ai.dialogue_manager import handle_message

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest):
    """Reçoit un message utilisateur (et l'identifiant de conversation en
    cours, s'il existe) et retourne la réponse générée par le chatbot.

    `request` est automatiquement validé/désérialisé par FastAPI à partir
    du JSON de la requête HTTP, grâce au schéma Pydantic ChatRequest.
    """
    result = handle_message(
        request.conversation_id,
        request.message,
    )
    # `**result` déballe le dict {"conversation_id": ..., "reply": ...}
    # retourné par handle_message pour construire l'objet ChatResponse,
    # que FastAPI sérialise ensuite en JSON pour la réponse HTTP.
    return ChatResponse(**result)
