"""
SmartLimo AI - Modèles ORM (SQLAlchemy)

Chaque classe ci-dessous représente une table de la base de données
PostgreSQL. SQLAlchemy utilise ces classes à la fois pour générer le
schéma SQL (via Base.metadata.create_all dans main.py) et pour manipuler
les lignes de ces tables sous forme d'objets Python dans tout le backend.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Date, Time, ForeignKey,
    DateTime, UniqueConstraint,
)
from sqlalchemy.sql import func
from datetime import datetime
from app.database import Base
from sqlalchemy.orm import relationship


class User(Base):
    """Un client de SmartLimo. Identifié par son email (unique), qui sert
    de clé de recherche pour retrouver l'historique de réservations d'un
    client (voir reservation_service.get_user_reservations)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    # server_default=func.now() : la date de création est calculée côté
    # base de données (fonction SQL NOW()) au moment de l'insertion, plutôt
    # que côté application.
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Vehicle(Base):
    """Un type de véhicule de la flotte (ex: Sedan, Sprinter VAN), avec sa
    capacité (passagers/bagages) et son tarif kilométrique. Une seule ligne
    par TYPE de véhicule (pas par véhicule physique individuel)."""
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    luggage = Column(Integer, nullable=False)
    price_per_km = Column(Float, nullable=False)
    status = Column(String, default="available")  # available / busy / maintenance


class Driver(Base):
    """Un chauffeur, avec sa position géographique courante (latitude/
    longitude) utilisée potentiellement pour le suivi en temps réel."""
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String, default="available")  # available / on_trip / offline


class Reservation(Base):
    """Une réservation de course, cœur métier de l'application. Relie un
    client (user_id), un véhicule (vehicle_id) et tous les détails du
    trajet collectés par le chatbot (lieux, date/heure, passagers,
    bagages, prix estimé)."""
    __tablename__ = "reservations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    service_type = Column(String, nullable=False)   # airport / hourly / point_to_point
    pickup_location = Column(String, nullable=False)
    dropoff_location = Column(String)
    pickup_date = Column(Date, nullable=False)
    pickup_time = Column(Time, nullable=False)
    passengers = Column(Integer, default=1)
    luggage = Column(Integer, default=0)
    child_seat_requested = Column(Boolean, default=False)  # True si le client a demande un siege enfant pour cette course
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    # `relationship` permet d'accéder directement à l'objet Vehicle complet
    # via `reservation.vehicle` (au lieu de juste son id), sans requête
    # SQL manuelle supplémentaire.
    vehicle = relationship("Vehicle")
    status = Column(String, default="pending")      # pending / confirmed / completed / cancelled
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    """Un paiement associé à une réservation. Actuellement non relié à un
    fournisseur de paiement réel (pas d'intégration Stripe/PayPal visible
    dans le code) - sert de table de suivi/statut."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String)                          # card / cash / paypal
    status = Column(String, default="pending")       # pending / paid / refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Zone(Base):
    """Une zone tarifaire (ex: MCO, PORT, DISNEY, UNIVERSAL...), telle que
    définie dans TEMPLATE_Zones.xlsx. Sert de point d'ancrage pour les
    codes postaux/villes qui la composent et pour la grille de tarifs
    fixes (Rate), qui référence des zones en origine et en destination."""
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)  # "Zone Code" (ex: MCO, PORT)
    description = Column(String)  # "Zone Description"
    state = Column(String)        # "State"


class ZoneZipcode(Base):
    """Un code postal appartenant à une zone. unique=True car un code
    postal donné (ex: 32819) n'appartient qu'à une seule zone dans la
    grille source - contrairement aux villes (voir ZoneCity)."""
    __tablename__ = "zone_zipcodes"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    zipcode = Column(String, unique=True, index=True, nullable=False)

    zone = relationship("Zone")


class ZoneCity(Base):
    """Une ville appartenant à une zone. Volontairement NON unique : une
    même ville peut apparaître dans plusieurs zones de la grille source
    (ex: villes limitrophes rattachées à des zones différentes selon le
    découpage métier), donc pas de contrainte d'unicité sur `city`."""
    __tablename__ = "zone_cities"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    city = Column(String, index=True, nullable=False)

    zone = relationship("Zone")


class Rate(Base):
    """Une ligne de la grille de tarifs fixes (TEMPLATE_Rates.xlsx) : le
    prix pour un code véhicule donné entre une zone d'origine et une zone
    de destination. `vehicle_code` reste le code brut de la grille
    (CHEVY/ESCALADE/GMC/SPRINTER/TRANSIT) et n'est PAS encore relié à
    Vehicle.name (voir le mapping à valider dans import_pricing.py) :
    ce lien sera fait au moment où estimate_price sera réécrit.
    tolls/parking/tax1/tax2 sont nullable car vides dans le template
    actuel, mais la grille peut les remplir plus tard."""
    __tablename__ = "rates"
    __table_args__ = (
        UniqueConstraint(
            "vehicle_code", "zone_from_id", "zone_to_id",
            name="uq_rate_vehicle_zone_from_zone_to",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    vehicle_code = Column(String, nullable=False, index=True)  # "Vehicle Code" brut de la grille
    zone_from_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    zone_to_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    rate = Column(Float, nullable=False)          # "Rate"
    tolls = Column(Float, nullable=True)          # "Tolls"
    parking = Column(Float, nullable=True)        # "Parking"
    tax1 = Column(Float, nullable=True)           # "Tax 1"
    tax2 = Column(Float, nullable=True)           # "Tax 2"
    matrix = Column(String)                       # "Matrix"
    is_default_matrix = Column(Boolean)            # "Is Default Matrix"

    zone_from = relationship("Zone", foreign_keys=[zone_from_id])
    zone_to = relationship("Zone", foreign_keys=[zone_to_id])


class HourlyRate(Base):
    """Tarif de location à l'heure (hors trajet zone-à-zone), par code
    véhicule, tel que défini par le rate card (tarifs horaires). Ce
    référentiel de véhicules (SEDAN, PREMIUM SEDAN, SUV, PREMIUM SUV, VAN,
    SPRINTER EXECUTIVE, LIMOUSINE, PARTY BUS, MINI BUS) est distinct de
    celui de Rate : les deux modes de tarification ne découpent pas la
    flotte de la même façon dans les documents source - pas de mapping
    tenté entre les deux ici."""
    __tablename__ = "hourly_rates"

    id = Column(Integer, primary_key=True, index=True)
    vehicle_code = Column(String, unique=True, nullable=False, index=True)
    hourly_rate = Column(Float, nullable=False)
    minimum_hours = Column(Integer, nullable=False)
    notice_hours = Column(Integer, nullable=False)  # préavis minimum avant la prise en charge


class Surcharge(Base):
    """Un supplément ou frais annexe (child seat, majoration nuit/jour
    férié, arrêt additionnel, frais aéroport, meet & greet, majoration
    rayon horaire...). Trop hétérogène pour être découpé en colonnes
    dédiées par règle : soit un montant fixe (amount), soit un pourcentage
    (percent), soit purement informatif (les deux à None, ex: gratuité
    non incluse par défaut)."""
    __tablename__ = "surcharges"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=False)
    amount = Column(Float, nullable=True)
    percent = Column(Float, nullable=True)
    description = Column(String, nullable=True)


class WaitTimeRule(Base):
    """Règle de temps d'attente gratuit (grace period) et de facturation
    au-delà, par type de trajet (vol domestique / international / prise
    en charge locale)."""
    __tablename__ = "wait_time_rules"

    id = Column(Integer, primary_key=True, index=True)
    trip_type = Column(String, unique=True, nullable=False, index=True)  # DOMESTIC / INTERNATIONAL / LOCAL
    grace_period_minutes = Column(Integer, nullable=False)
    increment_minutes = Column(Integer, nullable=False)
    rate_per_increment = Column(Float, nullable=False)
