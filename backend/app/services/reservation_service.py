from datetime import datetime, timedelta, date, time

import dateparser
from sqlalchemy.orm import Session

from app.models import User, Reservation


def get_or_create_user(db: Session, name: str, email: str, phone: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(name=name, email=email, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def parse_date(raw: str) -> date:
    parsed = dateparser.parse(raw, settings={"PREFER_DATES_FROM": "future"})
    if parsed:
        return parsed.date()
    return datetime.now().date() + timedelta(days=1)


def parse_time(raw: str) -> time:
    parsed = dateparser.parse(raw)
    if parsed:
        return parsed.time()
    return time(12, 0)


def create_reservation(db: Session, slots: dict) -> Reservation:
    user = get_or_create_user(
        db,
        name=slots.get("name", ""),
        email=slots.get("email", ""),
        phone=slots.get("phone", ""),
    )

    reservation = Reservation(
        user_id=user.id,
        service_type=slots.get("service_type") or "point_to_point",
        pickup_location=slots.get("pickup_location", ""),
        dropoff_location=slots.get("dropoff_location", ""),
        pickup_date=parse_date(str(slots.get("date", ""))),
        pickup_time=parse_time(str(slots.get("time", ""))),
        passengers=slots.get("passengers") or 1,
        luggage=slots.get("luggage") if slots.get("luggage") is not None else 0,
        status="confirmed",
    )
    db.add(reservation)
    db.commit()
    db.refresh(reservation)
    return reservation



def cancel_reservation(db: Session, reservation_id: int) -> bool:
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if reservation:
        reservation.status = "cancelled"
        db.commit()
        return True
    return False


def get_user_reservations(db: Session, email: str = None, phone: str = None) -> list[Reservation]:
    if email:
        user = db.query(User).filter(User.email == email).first()
    elif phone:
        user = db.query(User).filter(User.phone == phone).first()
    else:
        return []

    if not user:
        return []

    return (
        db.query(Reservation)
        .filter(Reservation.user_id == user.id)
        .order_by(Reservation.pickup_date.desc(), Reservation.pickup_time.desc())
        .all()
    )