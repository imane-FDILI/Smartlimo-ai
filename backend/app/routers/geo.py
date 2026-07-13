from fastapi import APIRouter

from app.services.geo_service import get_route

router = APIRouter(prefix="/route", tags=["Geo"])


@router.get("/")
def route(pickup: str, dropoff: str):
    """Retourne le trajet (distance/duree/coordonnees) entre deux lieux via geo_service."""
    result = get_route(pickup, dropoff)
    if result is None:
        return {"error": "Route not found"}
    return result