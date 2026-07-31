"""
SmartLimo AI - Router des réservations

Expose des routes de LECTURE des réservations (listing complet, recherche
par client, détail par id). La CRÉATION/modification/annulation des
réservations passe uniquement par le chatbot (dialogue_manager), ce
router ne fait donc que consulter les données déjà en base.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reservation
from app.services.reservation_service import get_user_reservations

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("/")
def list_reservations(db: Session = Depends(get_db)):
    """Retourne toutes les réservations, tous clients confondus.

    `Depends(get_db)` fait injecter par FastAPI une session de base de
    données (voir database.get_db) valable le temps de cette requête,
    fermée automatiquement une fois la réponse envoyée.
    """
    return db.query(Reservation).all()


@router.get("/user")
def list_user_reservations(email: str = None, phone: str = None, db: Session = Depends(get_db)):
    """Retourne les réservations d'un client identifié par son email et/ou
    son téléphone (paramètres de requête optionnels)."""
    return get_user_reservations(db, email=email, phone=phone)


@router.get("/{reservation_id}")
def get_reservation(reservation_id: int, db: Session = Depends(get_db)):
    """Retourne le détail d'une réservation précise via son id (extrait de
    l'URL, ex: GET /reservations/42)."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if reservation is None:
        return {"error": "Reservation not found"}
    return reservation
