"""
SmartLimo AI - Service de recommandation de véhicule (règle simple)

NOTE IMPORTANTE : ce fichier n'est actuellement importé nulle part dans le
reste du projet. La fonction réellement utilisée par le chatbot pour
recommander un véhicule est recommend_vehicle dans
app/services/reservation_service.py (même nom de fonction, logique très
proche). Ce fichier semble être une version antérieure ou en double,
conservée mais non branchée.
"""

from sqlalchemy.orm import Session

from app.models import Vehicle


def recommend_vehicle(db: Session, passengers: int, luggage: int):
    """
    Retourne le meilleur véhicule disponible.

    Parcourt les véhicules dont le statut est "available", triés par
    capacité croissante, et retourne le premier qui peut accueillir à la
    fois le nombre de passagers et de bagages demandés (donc le plus
    petit véhicule suffisant). Retourne None si aucun véhicule disponible
    ne convient.
    """

    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.status == "available")
        .order_by(Vehicle.capacity.asc())
        .all()
    )

    for vehicle in vehicles:
        if (
            vehicle.capacity >= passengers
            and vehicle.luggage >= luggage
        ):
            return vehicle

    return None
