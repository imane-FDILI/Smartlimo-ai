"""
SmartLimo AI - Script d'initialisation de la flotte de véhicules

À exécuter une fois manuellement (`python -m app.seed_vehicles` depuis
backend/) pour peupler la table `vehicles` avec les modèles disponibles.
Sans données de flotte, le service de recommandation et le calcul de prix
n'auraient aucun véhicule à proposer.
"""

from app.database import SessionLocal
from app.models import Vehicle

# Catalogue de référence de la flotte SmartLimo : nom, capacité en
# passagers, capacité en bagages, et tarif au kilomètre pour chaque type
# de véhicule.
FLEET = [
    {"name": "Sedan", "capacity": 3, "luggage": 3, "price_per_km": 2.5},
    {"name": "Executive SUV", "capacity": 6, "luggage": 6, "price_per_km": 3.5},
    {"name": "Premium SUV", "capacity": 6, "luggage": 8, "price_per_km": 4.0},
    {"name": "Transit VAN", "capacity": 14, "luggage": 14, "price_per_km": 4.5},
    {"name": "Sprinter VAN", "capacity": 11, "luggage": 12, "price_per_km": 5.0},
]

def seed():
    """Insère chaque véhicule de FLEET s'il n'existe pas déjà en base
    (recherche par nom), de façon à pouvoir relancer ce script plusieurs
    fois sans créer de doublons (idempotent)."""
    db = SessionLocal()
    try:
        for v in FLEET:
            existing = db.query(Vehicle).filter(Vehicle.name == v["name"]).first()
            if not existing:
                # `**v` déballe le dict en arguments nommés du constructeur
                # Vehicle (name=..., capacity=..., etc.).
                db.add(Vehicle(**v))
        db.commit()
        print("Flotte inseree :", db.query(Vehicle).count(), "vehicules")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
