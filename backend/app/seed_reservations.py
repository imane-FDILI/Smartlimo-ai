"""
SmartLimo AI - Reservations de demonstration

A executer une fois manuellement (`python -m app.seed_reservations` depuis
backend/) pour peupler la table `reservations` avec quelques courses
fictives mais realistes, afin que le dashboard/la liste de reservations ne
soit pas vide pendant la soutenance.

Reutilise reservation_service.create_reservation() et
estimate_price_by_zone() - les memes fonctions que le chatbot en
production - pour que les prix affiches soient strictement coherents avec
la grille tarifaire reelle (seed_demo_pricing.py) plutot que des chiffres
inventes a la main.

Idempotent : si une reservation existe deja pour le premier email de test
ci-dessous, le script ne fait rien (evite les doublons a chaque relance).
Necessite que seed_vehicles.py et seed_demo_pricing.py aient deja ete
executes (flotte + grille de tarifs).
"""

from datetime import date, timedelta

from app.database import SessionLocal
from app.models import User, Reservation
from app.services.reservation_service import (
    create_reservation, estimate_price_by_zone, apply_surcharges,
)

# (nom, email, telephone, service_type, pickup, dropoff, vehicule,
#  jours depuis aujourd'hui, heure, passagers, bagages, siege enfant)
SAMPLE_RESERVATIONS = [
    ("Sarah Johnson", "sarah.johnson@example.com", "+1 407-555-0142",
     "from_airport", "Orlando International Airport", "Walt Disney World",
     "Sedan", 3, "2:00 PM", 2, 2, False),
    ("Marc Dubois", "marc.dubois@example.com", "+1 407-555-0198",
     "from_airport", "Orlando International Airport", "Universal Studios",
     "Executive SUV", 5, "10:30 AM", 5, 4, False),
    ("Amina El Amrani", "amina.elamrani@example.com", "+1 321-555-0176",
     "from_port", "Port Canaveral", "Walt Disney World",
     "Sprinter VAN", -2, "4:00 PM", 9, 8, True),
    ("James Whitfield", "james.whitfield@example.com", "+1 407-555-0111",
     "from_airport", "Orlando Sanford International Airport", "Legoland",
     "Premium SUV", 7, "1:15 PM", 4, 5, True),
    ("Laura Martinez", "laura.martinez@example.com", "+1 407-555-0163",
     "from_airport", "Orlando International Airport", "Kissimmee",
     "Transit VAN", 1, "6:00 AM", 12, 10, False),
    ("David Chen", "david.chen@example.com", "+1 407-555-0129",
     "from_airport", "Orlando International Airport", "Davenport",
     "Sedan", -10, "11:00 AM", 2, 1, False),
    ("Fatima Zahra", "fatima.zahra@example.com", "+1 321-555-0154",
     "from_port", "Port Canaveral", "Kissimmee",
     "Executive SUV", 14, "3:30 PM", 6, 6, False),
    ("Robert Miller", "robert.miller@example.com", "+1 407-555-0187",
     "from_airport", "Orlando International Airport", "Universal Studios",
     "Sprinter VAN", -1, "9:00 PM", 8, 7, False),
]

# Reservations passees (jours negatifs) auxquelles on assigne un statut
# different de "confirmed" apres coup, pour varier l'affichage.
STATUS_OVERRIDES = {
    "amina.elamrani@example.com": "completed",
    "david.chen@example.com": "completed",
    "robert.miller@example.com": "cancelled",
}


def already_seeded(db) -> bool:
    first_email = SAMPLE_RESERVATIONS[0][1]
    user = db.query(User).filter(User.email == first_email).first()
    if user is None:
        return False
    return db.query(Reservation).filter(Reservation.user_id == user.id).count() > 0


def seed():
    db = SessionLocal()
    try:
        if already_seeded(db):
            print("Reservations de demo deja presentes, rien a faire.")
            return

        created = 0
        for (name, email, phone, service_type, pickup, dropoff, vehicle,
             days_offset, time_str, passengers, luggage, child_seat) in SAMPLE_RESERVATIONS:

            price = estimate_price_by_zone(db, pickup, dropoff, vehicle)
            if price is not None:
                price = apply_surcharges(db, price, None, None, pickup, dropoff)

            pickup_date = date.today() + timedelta(days=days_offset)

            slots = {
                "name": name,
                "email": email,
                "phone": phone,
                "vehicle": vehicle,
                "service_type": service_type,
                "pickup_location": pickup,
                "dropoff_location": dropoff,
                "date": pickup_date.strftime("%B %d, %Y"),
                "time": time_str,
                "passengers": passengers,
                "luggage": luggage,
                "child_seat_requested": child_seat,
                "estimated_price": price,
            }

            reservation = create_reservation(db, slots)

            override = STATUS_OVERRIDES.get(email)
            if override:
                reservation.status = override
                db.commit()

            created += 1

        print(f"Reservations de demo creees : {created}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
