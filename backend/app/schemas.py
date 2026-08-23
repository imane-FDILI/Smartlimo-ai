"""
SmartLimo AI - Schémas Pydantic (validation des requêtes/réponses HTTP)

Ces classes définissent la forme exacte des données échangées avec l'API
de chat. FastAPI les utilise automatiquement pour valider le JSON entrant
(ChatRequest) et sérialiser la réponse sortante (ChatResponse), en
rejetant avec une erreur 422 toute requête qui ne respecte pas ce format.
"""

from pydantic import BaseModel


class ChatRequest(BaseModel):
    """Corps JSON attendu pour POST /chat/.
    - message : le texte tapé par l'utilisateur (obligatoire)
    - conversation_id : identifiant de la conversation en cours, absent
      (None) lors du tout premier message d'un nouvel utilisateur - le
      dialogue manager en génère alors un nouveau (voir handle_message)."""
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    """Corps JSON retourné par POST /chat/.
    - reply : le texte de réponse du chatbot à afficher à l'utilisateur
    - conversation_id : à renvoyer par le frontend lors du message
      suivant, pour que le backend retrouve la bonne session/contexte."""
    reply: str
    conversation_id: str
