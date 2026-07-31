"""
SmartLimo AI - Configuration de la base de données

Centralise la connexion SQLAlchemy à la base (moteur, fabrique de sessions,
classe Base pour les modèles ORM) ainsi que la dépendance FastAPI `get_db`
utilisée par les routers pour obtenir une session de base de données par
requête HTTP.
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.ext.declarative import declarative_base

# Charge les variables d'environnement définies dans le fichier .env
# (notamment DATABASE_URL) dans os.environ.
load_dotenv()
# URL de connexion à la base (ex: postgresql://user:password@host/dbname),
# lue depuis la variable d'environnement DATABASE_URL pour ne jamais
# stocker d'identifiants en clair dans le code source.
DATABASE_URL = os.getenv("DATABASE_URL")

# Creer le moteur
# Le "moteur" SQLAlchemy gère le pool de connexions physiques vers la base
# de données ; il est créé une seule fois et réutilisé pour toute la durée
# de vie de l'application.
engine = create_engine(DATABASE_URL)

# Session locale pour interagir avec la base de données
# `sessionmaker` produit une "fabrique" de sessions : chaque appel à
# SessionLocal() crée une nouvelle session indépendante, liée au moteur
# ci-dessus. autocommit=False et autoflush=False signifient que les
# changements ne sont écrits en base que sur un `commit()` explicite,
# ce qui donne un contrôle précis des transactions.
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine)

# Base pour les modeles
# Toutes les classes de modèles ORM (voir models.py) héritent de cette
# classe `Base`, ce qui permet à SQLAlchemy de savoir quelles classes
# correspondent à des tables et de générer le schéma correspondant.
Base = declarative_base()

# Dépendance FastAPI : fournit une session DB par requête
# Utilisée dans les routers via `Depends(get_db)`. Le `yield` fait de
# cette fonction un générateur : FastAPI exécute le code avant le yield,
# fournit `db` à la route le temps de traiter la requête, puis exécute le
# code après le yield (ici, la fermeture de la session) une fois la
# réponse envoyée - même en cas d'exception grâce au `finally`.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
