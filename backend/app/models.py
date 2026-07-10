from sqlalchemy import Column, Integer, String, Float, Date, Time, ForeignKey, DateTime
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    phone = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    capacity = Column(Integer, nullable=False)
    luggage = Column(Integer, nullable=False)
    price_per_km = Column(Float, nullable=False)
    status = Column(String, default="available")  # available / busy / maintenance


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String, default="available")  # available / on_trip / offline


class Reservation(Base):
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
    vehicle_id = Column(Integer, ForeignKey("vehicles.id"))
    status = Column(String, default="pending")      # pending / confirmed / completed / cancelled
    price = Column(Float)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    reservation_id = Column(Integer, ForeignKey("reservations.id"), nullable=False)
    amount = Column(Float, nullable=False)
    method = Column(String)                          # card / cash / paypal
    status = Column(String, default="pending")       # pending / paid / refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    