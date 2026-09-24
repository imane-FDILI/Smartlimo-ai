"""
SmartLimo AI - Service des réservations

Contient toute la logique métier liée aux réservations : création,
annulation, modification, recherche par client, calcul de prix et
recommandation de véhicule. C'est le service le plus utilisé par
dialogue_manager.py, qui l'appelle à chaque étape clé de la conversation
(confirmation, annulation, devis, etc.).
"""

from datetime import datetime, timedelta, date, time

import dateparser
from sqlalchemy.orm import Session

from app.models import User, Reservation, Vehicle, Zone, Rate, Surcharge
from app.services.geo_service import get_route
import re
import holidays as holidays_lib


def is_booking_in_advance(pickup_date, pickup_time, min_hours: int = 24) -> bool:
    """Verifie que la reservation est faite au moins min_hours avant le depart."""
    if pickup_date is None or pickup_time is None:
        return True  # pas assez d'info pour verifier, on laisse passer
    pickup_datetime = datetime.combine(pickup_date, pickup_time)
    now = datetime.now()
    return pickup_datetime - now >= timedelta(hours=min_hours)


def is_us_holiday(check_date) -> bool:
    """Verifie si une date est un jour ferie federal americain,
    pour n'importe quelle annee (calcul dynamique, pas de liste figee)."""
    us_holidays = holidays_lib.UnitedStates(years=check_date.year)
    return check_date in us_holidays

def apply_surcharges(db: Session, base_price: float, pickup_time, pickup_date, pickup_location: str, dropoff_location: str) -> float:
    """Applique les suppléments simples (nuit, jour férié, frais aéroport/port)."""
    total = base_price

    # Supplement nuit (deja fait)
    early_late = db.query(Surcharge).filter(Surcharge.code == "EARLY_LATE").first()
    if early_late and pickup_time is not None and 0 <= pickup_time.hour < 5:
        total += early_late.amount

    # Supplement jour ferie (deja fait)
    holiday = db.query(Surcharge).filter(Surcharge.code == "HOLIDAY_SURCHARGE").first()
    if holiday and pickup_date is not None and is_us_holiday(pickup_date):
        total += total * (holiday.percent / 100)

    # NOUVEAU : frais aeroport (si pickup = MCO ou SFB)
    pickup_lower = pickup_location.lower()
    if "mco" in pickup_lower or "airport" in pickup_lower or "sanford" in pickup_lower or "sfb" in pickup_lower:
        airport_fee = db.query(Surcharge).filter(Surcharge.code == "AIRPORT_FEE_PORT_CANAVERAL").first()
        if airport_fee and airport_fee.amount:
            total += airport_fee.amount

    # NOUVEAU : frais Port Canaveral (si pickup OU dropoff = port)
    dropoff_lower = dropoff_location.lower()
    if "port canaveral" in pickup_lower or "port canaveral" in dropoff_lower or "cocoa beach" in pickup_lower or "cocoa beach" in dropoff_lower:
        port_fee = db.query(Surcharge).filter(Surcharge.code == "SERVICE_FEE").first()
        if port_fee and port_fee.amount:
            total += port_fee.amount

    return round(total, 2)

def get_or_create_user(db: Session, name: str, email: str, phone: str) -> User:
    """Retrouve un utilisateur existant par son email, ou en crée un
    nouveau si aucun ne correspond. L'email sert donc de clé d'identité
    du client (voir aussi le champ `unique` sur User.email dans models.py)."""
    user = db.query(User).filter(User.email == email).first()
    if user:
        return user
    user = User(name=name, email=email, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)  # recharge l'objet depuis la base pour récupérer son id généré
    return user


def parse_date(raw: str) -> date:
    """Convertit une date écrite en langage naturel (ex: "tomorrow",
    "next Friday", "22 July") en objet `date` Python, grâce à la librairie
    `dateparser`. PREFER_DATES_FROM="future" évite qu'une date comme
    "Friday" soit interprétée comme un vendredi déjà passé.
    Si le texte n'est pas compris, on retombe sur "demain" par défaut
    plutôt que d'échouer (une réservation a besoin d'une date valide)."""
    parsed = dateparser.parse(raw, settings={"PREFER_DATES_FROM": "future"})
    if parsed:
        return parsed.date()
    return datetime.now().date() + timedelta(days=1)


def parse_time(raw: str):
    text = raw.strip().lower()
    if "midnight" in text:
        return time(0, 0)
    if "noon" in text:
        return time(12, 0)
    parsed = dateparser.parse(raw)
    return parsed.time() if parsed else None

def is_time_unambiguous(raw: str) -> bool:
    text = raw.strip().lower()
    if "midnight" in text or "noon" in text:
        return True
    if re.search(r"(am|pm|a\.m\.|p\.m\.)\b", text, re.I):
        return True
    if re.search(r"^\d{1,2}:\d{2}$", text):
        return True
    return False


def create_reservation(db: Session, slots: dict) -> Reservation:
    """Crée la réservation en base à partir des slots collectés par le
    dialogue manager. Récupère (ou crée) d'abord le client, puis résout
    le nom de véhicule choisi en son id réel, avant d'insérer la ligne
    Reservation avec le statut "confirmed" (la confirmation utilisateur a
    déjà eu lieu à ce stade du dialogue)."""
    user = get_or_create_user(
        db,
        name=slots.get("name", ""),
        email=slots.get("email", ""),
        phone=slots.get("phone", ""),
    )
    # Recherche du véhicule par son nom (ex: "Sedan") pour récupérer son id ;
    # si le nom ne correspond à aucun véhicule (ex: "No Preference"),
    # vehicle_id restera None.
    vehicle = db.query(Vehicle).filter(Vehicle.name == slots.get("vehicle")).first()

    reservation = Reservation(
        user_id=user.id,
        vehicle_id=vehicle.id if vehicle else None,
        service_type=slots.get("service_type") or "point_to_point",
        pickup_location=slots.get("pickup_location", ""),
        dropoff_location=slots.get("dropoff_location", ""),
        pickup_date=parse_date(str(slots.get("date", ""))),
        pickup_time=parse_time(str(slots.get("time", ""))),
        passengers=slots.get("passengers") or 1,
        # Contrairement à `or 1` ci-dessus pour passengers, on vérifie
        # explicitement `is not None` pour luggage car 0 est une valeur
        # valide qui ne doit pas être remplacée par une valeur par défaut.
        luggage=slots.get("luggage") if slots.get("luggage") is not None else 0,
        child_seat_requested=slots.get("child_seat_requested", False),
        status="confirmed",
        price=slots.get("estimated_price"),
    )
    
    db.add(reservation)
    db.commit()
    db.refresh(reservation)  # récupère l'id généré et les valeurs par défaut serveur
    return reservation



def cancel_reservation(db: Session, reservation_id: int) -> bool:
    """Passe le statut d'une réservation à "cancelled". Ne supprime jamais
    la ligne en base (conservation de l'historique), retourne False si la
    réservation n'existe pas."""
    reservation = db.query(Reservation).filter(Reservation.id == reservation_id).first()
    if reservation:
        reservation.status = "cancelled"
        db.commit()
        return True
    return False


def get_user_reservations(db, email=None, phone=None):
    """Retourne toutes les réservations actives (non annulées) associées à
    l'email et/ou au téléphone fourni (liste vide si le client est inconnu
    ou s'il n'a aucune réservation)."""
    query = db.query(User)
    if email:
        query = query.filter(User.email == email)
    if phone:
        query = query.filter(User.phone == phone)
    user = query.first()
    if user is None:
        return []
    return db.query(Reservation).filter(
        Reservation.user_id == user.id,
        Reservation.status != "cancelled"
    ).all()

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
    """Recommande le véhicule le plus adapté : le plus petit (par
    capacité croissante) qui peut accueillir à la fois le nombre de
    passagers et de bagages demandés. C'est cette fonction (et non celle
    de services/recommendation_service.py ni le modèle entraîné par
    train_recommender.py) qui est réellement utilisée par le chatbot.
    Ne filtre pas sur le statut "available" du véhicule (contrairement à
    recommendation_service.recommend_vehicle) : retourne le premier type
    de véhicule suffisant, indépendamment de sa disponibilité réelle."""
    return db.query(Vehicle).filter(
        Vehicle.capacity >= passengers,
        Vehicle.luggage >= luggage
    ).order_by(Vehicle.capacity).first()

VEHICLE_NAME_TO_RATE_CODE = {
    "Sedan": "SEDAN",
    "Executive SUV": "SUV",
    "Transit VAN": "VAN",
    "Sprinter VAN": "SPRINTER VAN",
    "Premium SUV": "LIMOUSINE",
}

PICKUP_KEYWORDS = {
    "MCO": ["mco", "orlando international airport"],
    "SFB": ["sanford", "sfb"],
    "PORT": ["port canaveral", "port", "cruise"],
}


def resolve_pickup_zone_code(pickup_text: str) -> str | None:
    """Reconnait l'origine (MCO/SFB/PORT) par mot-cle simple dans le texte."""
    text = pickup_text.lower()
    for zone_code, keywords in PICKUP_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return zone_code
    return None


DROPOFF_KEYWORDS = {
    "DISNEY - LAKE B VISTA": ["disney", "lake buena vista"],
    "UNIVERSAL": ["universal"],
    "KISSIMMEE - SOUTH AREA": ["kissimmee", "celebration"],
    "DAVENPORT": ["davenport", "champions gate"],
    "LEGOLAND": ["legoland", "lego land"],
    "PORT": ["port canaveral", "cocoa beach"],
}


def resolve_dropoff_zone_code(db: Session, dropoff_text: str) -> str | None:
    """Reconnaît la destination (zone) par mot-cle simple dans le texte."""
    if not dropoff_text:
        return None
    text = dropoff_text.lower()
    for zone_code, keywords in DROPOFF_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return zone_code
    return None


def estimate_price_by_zone(db: Session, pickup: str, dropoff: str, vehicle_name: str) -> float | None:
    """Calcule le prix en cherchant un tarif fixe dans la grille zone-a-zone."""
    zone_from_code = resolve_pickup_zone_code(pickup)
    if zone_from_code is None:
        return None

    zone_to_code = resolve_dropoff_zone_code(db, dropoff)
    if zone_to_code is None:
        return None

    rate_code = VEHICLE_NAME_TO_RATE_CODE.get(vehicle_name)
    if rate_code is None:
        return None

    zone_from = db.query(Zone).filter(Zone.code == zone_from_code).first()
    zone_to = db.query(Zone).filter(Zone.code == zone_to_code).first()
    if not zone_from or not zone_to:
        return None

    rate = db.query(Rate).filter(
        Rate.vehicle_code == rate_code,
        Rate.zone_from_id == zone_from.id,
        Rate.zone_to_id == zone_to.id,
    ).first()

    if rate is None:
        return None

    total = rate.rate
    if rate.tolls:
        total += rate.tolls
    if rate.parking:
        total += rate.parking
    return round(total, 2)

def is_vehicle_available(db: Session, vehicle_name: str, pickup_date, pickup_time) -> bool:
    """Verifie qu'aucune reservation active n'existe deja pour ce vehicule,
    a une heure proche de celle demandee (fenetre de 2h par defaut)."""
    vehicle = db.query(Vehicle).filter(Vehicle.name == vehicle_name).first()
    if vehicle is None:
        return True

    requested_dt = datetime.combine(pickup_date, pickup_time)
    window_start = (requested_dt - timedelta(hours=2)).time()
    window_end = (requested_dt + timedelta(hours=2)).time()

    existing = (
        db.query(Reservation)
        .filter(
            Reservation.vehicle_id == vehicle.id,
            Reservation.pickup_date == pickup_date,
            Reservation.status.in_(["pending", "confirmed"]),
        )
        .all()
    )

    for res in existing:
        if window_start <= res.pickup_time <= window_end:
            return False

    return True

def get_eligible_vehicles(db: Session, passengers: int, luggage: int = 0):
    """Retourne les vehicules dont la capacite est suffisante, tries du plus petit au plus grand."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.capacity >= passengers,
        Vehicle.luggage >= luggage
    ).order_by(Vehicle.capacity).all()
    return [v.name for v in vehicles]