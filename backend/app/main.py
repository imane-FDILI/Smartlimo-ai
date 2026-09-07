"""
SmartLimo AI - Point d'entrée de l'API FastAPI

Ce fichier assemble l'application : création de l'instance FastAPI,
création automatique des tables en base au démarrage, configuration CORS
et enregistrement des différents routers (chat, réservations, géo).

Lancement typique : `uvicorn app.main:app --reload` depuis le dossier backend.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

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
# Autorise explicitement le frontend de production (Vercel) et l'environnement
# de développement local (Vite) à appeler cette API depuis le navigateur.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://smartlimo-ai-assistant.vercel.app",
        "http://localhost:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Filet de sécurité CORS : si une route lève une exception non gérée, la
# réponse 500 générée par Starlette passerait normalement au-dessus du
# CORSMiddleware (donc sans header Access-Control-Allow-Origin), ce que le
# navigateur signale à tort comme une erreur CORS. Ce handler est traité par
# ExceptionMiddleware, situé À L'INTÉRIEUR du CORSMiddleware, donc sa réponse
# reçoit bien les headers CORS.
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
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
