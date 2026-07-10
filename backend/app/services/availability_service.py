def is_vehicle_available(db: Session, slots: dict) -> bool:
    """Vérifie si un véhicule est disponible pour la réservation."""
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

    return len(existing_reservations) == 0