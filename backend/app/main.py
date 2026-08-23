"""
SmartLimo AI - Point d'entrée de l'API FastAPI

Ce fichier assemble l'application : création de l'instance FastAPI,
création automatique des tables en base au démarrage, configuration CORS
et enregistrement des différents routers (chat, réservations, géo).

Lancement typique : `uvicorn app.main:app --reload` depuis le dossier backend.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models
from app.routers import chat, reservations, geo

app = FastAPI(title="SmartLimo AI API")
app.include_router(geo.router)

# Crée les SmartLimo AItables dans PostgreSQL au démarrage
# `Base.metadata.create_all` inspecte tous les modèles définis dans
# `models.py` (importé ci-dessus juste pour déclencher cet enregistrement)
# et crée en base les tables qui n'existent pas encore. Ne modifie jamais
# les tables déjà existantes (pas de migration automatique des colonnes).
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# CORS
# Autorise le frontend (servi sur une autre origine/port, ex: localhost:5173
# en développement) à appeler cette API depuis le navigateur.
# allow_origins=["*"] : accepte les requêtes de n'importe quelle origine.
# ATTENTION : cette configuration est permissive, à restreindre en production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Chaque router regroupe les routes liées à un domaine fonctionnel :
# - reservations.router : création/consultation/modification des réservations
# - chat.router         : point d'entrée du chatbot (dialogue_manager)
# - geo.router          : calcul d'itinéraires / géolocalisation
app.include_router(
    reservations.router
    )

app.include_router(chat.router)


@app.get("/")
def read_root():
    """Route de vérification basique (health check) : confirme que l'API
    est démarrée et répond, sans dépendre de la base de données."""
    return {"message": "SmartLimo AI API is running"}
