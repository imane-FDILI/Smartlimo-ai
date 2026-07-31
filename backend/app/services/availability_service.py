"""
SmartLimo AI - Service de disponibilité des véhicules

NOTE IMPORTANTE : ce fichier n'est actuellement importé nulle part ailleurs
dans le projet (dialogue_manager.py ne l'utilise pas) et il lui manque des
imports indispensables pour fonctionner (Session, Reservation, parse_date,
parse_time ne sont pas importés ici) : tel quel, l'appeler provoquerait une
NameError. Il s'agit probablement d'une ébauche de fonctionnalité pas encore
branchée au reste de l'application.
"""

def is_vehicle_available(db: Session, slots: dict) -> bool:
    """Vérifie si un véhicule est disponible pour la réservation.

    Compare le véhicule demandé (slots["vehicle_id"]) à la même date/heure
    (slots["date"]/slots["time"]) avec les réservations déjà existantes en
    base : si au moins une réservation "pending" ou "confirmed" occupe déjà
    ce véhicule à ce créneau précis, il est considéré indisponible.
    """
    pickup_date = parse_date(str(slots.get("date", ""))) #. Conversion de la date
    pickup_time = parse_time(str(slots.get("time", "")))

    # Vérifier les réservations existantes pour le même véhicule
    existing_reservations = (
        db.query(Reservation)
        .filter(
            Reservation.vehicle_id == slots.get("vehicle_id"),
            Reservation.pickup_date == pickup_date,
            Reservation.pickup_time == pickup_time,
            Reservation.status.in_(["pending", "confirmed"]),
        )
        .all()
    )

    # Disponible seulement si aucune réservation concurrente n'a été trouvée.
    return len(existing_reservations) == 0
