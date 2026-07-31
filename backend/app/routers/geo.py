"""
SmartLimo AI - Router de géolocalisation

Expose une route GET /route/ qui permet au frontend (notamment le
composant TripMap) de récupérer un itinéraire (distance, durée,
coordonnées) entre deux lieux, sans passer par le chatbot.
"""

from fastapi import APIRouter

from app.services.geo_service import get_route

router = APIRouter(prefix="/route", tags=["Geo"])


@router.get("/")
def route(pickup: str, dropoff: str):
    """Retourne le trajet (distance/duree/coordonnees) entre deux lieux via geo_service.

    `pickup` et `dropoff` sont passés en paramètres de requête (query
    params), ex: GET /route/?pickup=MCO&dropoff=Disney+World.
    """
    result = get_route(pickup, dropoff)
    if result is None:
        # L'un des deux lieux n'a pas pu être géolocalisé : on renvoie une
        # erreur "métier" en 200 plutôt qu'une exception HTTP, à charge du
        # frontend de vérifier la présence de la clé "error".
        return {"error": "Route not found"}
    return result
