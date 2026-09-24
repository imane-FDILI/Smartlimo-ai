"""
SmartLimo AI - Import de la grille de tarifs fixes (zones + rates)

À exécuter une fois manuellement (`python -m app.import_pricing` depuis
backend/) pour charger backend/data/pricing/TEMPLATE_Zones.xlsx et
TEMPLATE_Rates.xlsx dans les tables zones / zone_zipcodes / zone_cities /
rates. Idempotent : peut être relancé sans créer de doublons (upsert par
clé naturelle - code de zone pour Zone, triplet véhicule/zone_from/zone_to
pour Rate).

Peuple uniquement les tables de la grille fixe : le calcul de prix
lui-même vit dans reservation_service.estimate_price_by_zone.
"""

import os

import pandas as pd

from app.database import SessionLocal
from app.models import (
    Zone, ZoneZipcode, ZoneCity, Rate, HourlyRate, Surcharge, WaitTimeRule,
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "pricing")
ZONES_FILE = os.path.join(DATA_DIR, "TEMPLATE_Zones.xlsx")
RATES_FILE = os.path.join(DATA_DIR, "TEMPLATE_Rates.xlsx")
HOURLY_RATES_FILE = os.path.join(DATA_DIR, "TEMPLATE_HourlyRates.xlsx")
SURCHARGES_FILE = os.path.join(DATA_DIR, "TEMPLATE_Surcharges.xlsx")
WAIT_TIME_FILE = os.path.join(DATA_DIR, "TEMPLATE_WaitTime.xlsx")

# Mapping proposé code véhicule de la grille -> Vehicle.name de la flotte
# NLP (voir app/seed_vehicles.py). NON appliqué ici : Rate.vehicle_code
# garde le code brut de la grille. Ce mapping n'est qu'une proposition à
# valider avec le métier avant d'être utilisé dans le calcul de prix
# (SPRINTER/TRANSIT sont évidents par le nom ; CHEVY/GMC/ESCALADE ne le
# sont pas - rien ne garantit une bijection 1:1 avec les 5 véhicules de
# la flotte actuelle).
VEHICLE_CODE_TO_FLEET_NAME = {
    "SPRINTER": "Sprinter VAN",
    "TRANSIT": "Transit VAN",
    "CHEVY": None,     # TODO: à valider avec le métier
    "GMC": None,        # TODO: à valider avec le métier
    "ESCALADE": None,   # TODO: à valider avec le métier
}


def _split_list_cell(cell) -> list:
    """Découpe une cellule "a, b,c ,d" (espaces incohérents) en liste de
    valeurs nettoyées. Retourne [] pour une cellule vide (NaN)."""
    if pd.isna(cell):
        return []
    return [part.strip() for part in str(cell).split(",") if part.strip()]


def _normalize_postal_code(token) -> str:
    """Normalise un code postal individuel. Piège vérifié : la cellule
    "Postal Codes" de la zone UNIVERSAL ne contient qu'un seul code postal,
    qu'Excel/pandas stocke alors comme float (32819.0) plutôt que comme
    texte, faute de virgule pour forcer un type chaîne."""
    try:
        return str(int(float(token)))
    except (TypeError, ValueError):
        return str(token).strip()


def _split_postal_codes_cell(cell) -> list:
    if pd.isna(cell):
        return []
    if isinstance(cell, (int, float)):
        return [_normalize_postal_code(cell)]
    return [_normalize_postal_code(part) for part in str(cell).split(",") if part.strip()]


def _clean_float(value):
    """Convertit une cellule Excel vide (NaN) en None (plutôt qu'en NaN
    Python) pour que les colonnes nullable (tolls/parking/tax1/tax2)
    reçoivent bien NULL en base."""
    return None if pd.isna(value) else float(value)


def import_zones(db) -> dict:
    """Importe TEMPLATE_Zones.xlsx. Retourne un dict {code_zone: Zone}
    utilisé ensuite par import_rates pour résoudre zone_from/zone_to."""
    df = pd.read_excel(ZONES_FILE)
    zones_by_code = {}

    for _, row in df.iterrows():
        code = str(row["Zone Code"]).strip()

        zone = db.query(Zone).filter(Zone.code == code).first()
        if zone is None:
            zone = Zone(code=code)
            db.add(zone)

        zone.description = str(row["Zone Description"]).strip() if pd.notna(row["Zone Description"]) else None
        zone.state = str(row["State"]).strip() if pd.notna(row["State"]) else None
        db.flush()  # nécessaire pour obtenir zone.id avant d'insérer zipcodes/cities

        # Idempotent par remplacement : on reconstruit la liste des
        # zipcodes/villes de la zone à partir du fichier à chaque import,
        # plutôt que de tenter un diff ligne à ligne.
        db.query(ZoneZipcode).filter(ZoneZipcode.zone_id == zone.id).delete()
        db.query(ZoneCity).filter(ZoneCity.zone_id == zone.id).delete()

        for zipcode in _split_postal_codes_cell(row["Postal Codes"]):
            db.add(ZoneZipcode(zone_id=zone.id, zipcode=zipcode))
        for city in _split_list_cell(row["Cities in Zone"]):
            db.add(ZoneCity(zone_id=zone.id, city=city))

        zones_by_code[code] = zone

    db.commit()
    return zones_by_code


def import_rates(db, zones_by_code: dict) -> None:
    """Importe TEMPLATE_Rates.xlsx. La grille est volontairement à trous
    (zone_from ne vaut que MCO/PORT, et depuis PORT seules Disney et
    Universal sont tarifées) : ce script importe telles quelles les lignes
    présentes dans le fichier, sans tenter de générer les combinaisons
    manquantes - c'est au code de calcul de prix (pas encore écrit) de
    gérer l'absence de tarif pour une combinaison donnée."""
    df = pd.read_excel(RATES_FILE)

    for _, row in df.iterrows():
        vehicle_code = str(row["Vehicle Code"]).strip()
        zone_from_code = str(row["Zone From (Code)"]).strip()
        zone_to_code = str(row["Zone To (Code)"]).strip()

        zone_from = zones_by_code.get(zone_from_code)
        zone_to = zones_by_code.get(zone_to_code)
        if zone_from is None or zone_to is None:
            raise ValueError(
                f"Zone inconnue pour la ligne {vehicle_code} "
                f"{zone_from_code} -> {zone_to_code} "
                f"(TEMPLATE_Zones.xlsx doit être importé en premier et "
                f"contenir ces codes de zone)"
            )

        rate = db.query(Rate).filter(
            Rate.vehicle_code == vehicle_code,
            Rate.zone_from_id == zone_from.id,
            Rate.zone_to_id == zone_to.id,
        ).first()
        if rate is None:
            rate = Rate(vehicle_code=vehicle_code, zone_from_id=zone_from.id, zone_to_id=zone_to.id)
            db.add(rate)

        rate.rate = float(row["Rate"])
        rate.tolls = _clean_float(row["Tolls"])
        rate.parking = _clean_float(row["Parking"])
        rate.tax1 = _clean_float(row["Tax 1"])
        rate.tax2 = _clean_float(row["Tax 2"])
        rate.matrix = str(row["Matrix"]).strip() if pd.notna(row["Matrix"]) else None
        rate.is_default_matrix = bool(row["Is Default Matrix"]) if pd.notna(row["Is Default Matrix"]) else None

    db.commit()


def import_hourly_rates(db) -> None:
    """Importe TEMPLATE_HourlyRates.xlsx (tarifs à l'heure). Référentiel de
    véhicules distinct de celui de Rate (voir HourlyRate.__doc__)."""
    df = pd.read_excel(HOURLY_RATES_FILE)
    for _, row in df.iterrows():
        vehicle_code = str(row["Vehicle Code"]).strip()
        hourly_rate = db.query(HourlyRate).filter(HourlyRate.vehicle_code == vehicle_code).first()
        if hourly_rate is None:
            hourly_rate = HourlyRate(vehicle_code=vehicle_code)
            db.add(hourly_rate)
        hourly_rate.hourly_rate = float(row["Hourly Rate"])
        hourly_rate.minimum_hours = int(row["Minimum Hours"])
        hourly_rate.notice_hours = int(row["Notice Hours"])
    db.commit()


def import_surcharges(db) -> None:
    """Importe TEMPLATE_Surcharges.xlsx (suppléments et frais annexes)."""
    df = pd.read_excel(SURCHARGES_FILE)
    for _, row in df.iterrows():
        code = str(row["Code"]).strip()
        surcharge = db.query(Surcharge).filter(Surcharge.code == code).first()
        if surcharge is None:
            surcharge = Surcharge(code=code)
            db.add(surcharge)
        surcharge.label = str(row["Label"]).strip() if pd.notna(row["Label"]) else None
        surcharge.amount = _clean_float(row["Amount"])
        surcharge.percent = _clean_float(row["Percent"])
        surcharge.description = str(row["Description"]).strip() if pd.notna(row["Description"]) else None
    db.commit()


def import_wait_time_rules(db) -> None:
    """Importe TEMPLATE_WaitTime.xlsx (grace period / temps d'attente)."""
    df = pd.read_excel(WAIT_TIME_FILE)
    for _, row in df.iterrows():
        trip_type = str(row["Trip Type"]).strip()
        rule = db.query(WaitTimeRule).filter(WaitTimeRule.trip_type == trip_type).first()
        if rule is None:
            rule = WaitTimeRule(trip_type=trip_type)
            db.add(rule)
        rule.grace_period_minutes = int(row["Grace Period Minutes"])
        rule.increment_minutes = int(row["Increment Minutes"])
        rule.rate_per_increment = float(row["Rate Per Increment"])
    db.commit()


def run():
    db = SessionLocal()
    try:
        zones_by_code = import_zones(db)
        import_rates(db, zones_by_code)
        import_hourly_rates(db)
        import_surcharges(db)
        import_wait_time_rules(db)
        print("Zones importées :", len(zones_by_code))
        print("Tarifs zone-à-zone importés :", db.query(Rate).count())
        print("Tarifs horaires importés :", db.query(HourlyRate).count())
        print("Suppléments importés :", db.query(Surcharge).count())
        print("Règles de temps d'attente importées :", db.query(WaitTimeRule).count())
    finally:
        db.close()


if __name__ == "__main__":
    run()
