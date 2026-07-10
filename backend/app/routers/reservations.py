from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Reservation
from app.services.reservation_service import get_user_reservations

router = APIRouter(prefix="/reservations", tags=["Reservations"])


@router.get("/")
def list_reservations(db: Session = Depends(get_db)):
    return db.query(Reservation).all()


@router.get("/user")
def list_user_reservations(email: str = None, phone: str = None, db: Session = Depends(get_db)):
    return get_user_reservations(db, email=email, phone=phone)


@router.get("/{reservation_id}")
def get_reservation(reservation_id: int, db: Session = Depends(get_db)):
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if reservation is None:
        return {"error": "Reservation not found"}
    return reservation