import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base

load_dotenv()
# URL de connexion
DATABASE_URL = os.getenv("DATABASE_URL")

# Creer le moteur
engine = create_engine(DATABASE_URL)

# Session locale pour interagir avec la base de données
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False,
    bind=engine)

# Base pour les modeles
Base = declarative_base()

# Dépendance FastAPI : fournit une session DB par requête
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()