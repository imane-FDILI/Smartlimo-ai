"""
SmartLimo AI - Résolution de zones et tarifs fixes

Fait le lien entre le texte libre saisi dans le chat (pickup_location /
dropoff_location) et la grille de tarifs fixes (Zone/Rate) importée par
import_pricing.py, ainsi qu'entre Vehicle.name (flotte NLP) et
Rate.vehicle_code (grille). Utilisé par reservation_service.estimate_price
comme source de prix prioritaire ; le calcul par distance reste le repli
pour tout trajet ou véhicule non couvert par la grille.
"""

from sqlalchemy.orm import Session

from app.ai.entity_extractor import resolve_location
from app.models import Zone, Rate

# Mots-clés (en minuscules) reconnus dans un texte libre pour chaque zone.
# On retient la première zone dont un mot-clé apparaît dans le texte. À
# enrichir au fil de l'eau si de nouvelles formulations apparaissent côté
# utilisateurs (pas de géocodage : ces zones - Disney, Universal... -
# n'ont pas de zipcode réel dans nos données actuelles).
ZONE_KEYWORDS = {
    "MCO": ["mco", "orlando international"],
    "SFB": ["sfb", "sanford"],
    "PORT": ["port canaveral", "cape canaveral"],
    "DISNEY": ["disney"],
    "UNIVERSAL": ["universal"],
    "KISSIMMEE": ["kissimmee"],
    "DAVENPORT": ["davenport"],
    "LEGOLAND": ["lego land", "legoland"],
}

# Mapping flotte (Vehicle.name, NLP) -> code véhicule de la grille de
# tarifs fixes (Rate.vehicle_code). Proposé et à valider avec le métier :
# Executive SUV et Premium SUV partagent le même tarif "SUV" de la grille
# (pas de distinction premium dans la grille source) ; "LIMOUSINE" de la
# grille n'a pas d'équivalent dans la flotte actuelle.
VEHICLE_NAME_TO_RATE_CODE = {
    "Sedan": "SEDAN",
    "Executive SUV": "SUV",
    "Premium SUV": "SUV",
    "Transit VAN": "VAN",
    "Sprinter VAN": "SPRINTER VAN",
}


def resolve_zone(db: Session, location_text: str):
    """Retrouve la Zone correspondant à un texte libre (ex: "Orlando
    International Airport"), par recherche de mot-clé insensible à la
    casse. Passe d'abord par resolve_location (correction de fautes de
    frappe via le gazetteer, déjà utilisée par geo_service pour le
    géocodage) pour que "Sisney world" matche quand même "disney".
    Retourne None si aucun mot-clé ne correspond (trajet hors grille de
    tarifs fixes)."""
    if not location_text:
        return None
    text = resolve_location(location_text).lower()
    for zone_code, keywords in ZONE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            return db.query(Zone).filter(Zone.code == zone_code).first()
    return None


def get_fixed_rate(db: Session, pickup_location: str, dropoff_location: str, vehicle_name: str):
    """Cherche un tarif fixe pour ce trajet dans la grille zone-à-zone.
    La grille source ne définit les tarifs que dans un sens (depuis
    MCO/SFB/PORT vers les destinations) ; on tente aussi le sens inverse
    en supposant un tarif de transfert symétrique (convention standard du
    secteur, à valider avec le métier). Retourne None si la zone, le
    véhicule ou le tarif n'existe pas - le calcul par distance prend
    alors le relais côté appelant."""
    vehicle_code = VEHICLE_NAME_TO_RATE_CODE.get(vehicle_name)
    if vehicle_code is None:
        return None

    zone_from = resolve_zone(db, pickup_location)
    zone_to = resolve_zone(db, dropoff_location)
    if zone_from is None or zone_to is None:
        return None

    rate = db.query(Rate).filter(
        Rate.vehicle_code == vehicle_code,
        Rate.zone_from_id == zone_from.id,
        Rate.zone_to_id == zone_to.id,
    ).first()
    if rate is None:
        rate = db.query(Rate).filter(
            Rate.vehicle_code == vehicle_code,
            Rate.zone_from_id == zone_to.id,
            Rate.zone_to_id == zone_from.id,
        ).first()

    return rate.rate if rate else None
