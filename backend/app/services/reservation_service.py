from datetime import datetime, timedelta, date, time

import dateparser
from sqlalchemy.orm import Session

from app.models import User, Reservation, Vehicle
from app.services.geo_service import get_route


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


def get_user_reservations(db, email):
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return []
    return db.query(Reservation).filter(Reservation.user_id == user.id).all()

def get_reservation_route(db: Session, reservation_id: int):
    # Retourne le trajet (distance/duree/coordonnees) de la reservation via geo_service,
    # ou None si la reservation n'existe pas ou si un des lieux est introuvable.
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if reservation is None or not reservation.dropoff_location:
        return None
    return get_route(reservation.pickup_location, reservation.dropoff_location)


def update_reservation(db: Session, reservation_id: int, field: str, value) -> bool:
    # db: Session        -> la connexion base de donnees (le "panier")
    # reservation_id: int -> le numero de la reservation a modifier
    # field: str          -> le NOM de la colonne a changer (ex: "pickup_time")
    # value               -> la nouvelle valeur (pas de type precise : peut etre heure, date, texte...)
    # -> bool             -> la fonction promet de retourner True ou False

    # ETAPE 1 : chercher la ligne dont l'id correspond
    # .first() renvoie l'objet trouve, ou None si aucun
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()

    # ETAPE 2 : cas limite - reservation inexistante
    if reservation is None:
        return False

    # ETAPE 3 : modifier le champ dont le NOM est dans la variable field
    # setattr(objet, "nom_attribut", valeur) est l'equivalent dynamique de :
    #   reservation.pickup_time = valeur
    # mais ou "pickup_time" peut etre n'importe quelle colonne selon le cas
    setattr(reservation, field, value)

    # ETAPE 4 : enregistrer le changement dans PostgreSQL
    # (pas besoin de db.add() : l'objet vient de la base, SQLAlchemy
    #  detecte tout seul qu'il a ete modifie)
    db.commit()

    return True

def recommend_vehicle(db: Session, passengers: int, luggage: int = 0):
    return db.query(Vehicle).filter(
        Vehicle.capacity >= passengers,
        Vehicle.luggage >= luggage
    ).order_by(Vehicle.capacity).first()

def estimate_price(db: Session, distance_km: float, vehicle_name: str = None) -> float:
    vehicle = db.query(Vehicle).filter(Vehicle.name == vehicle_name).first()
    ppk = vehicle.price_per_km if vehicle else 3.0
    return round(10.0 + distance_km * ppk, 2)