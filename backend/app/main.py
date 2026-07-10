from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app import models
from app.routers import chat, reservations

app = FastAPI(title="SmartLimo AI API")


# Crée les SmartLimo AItables dans PostgreSQL au démarrage
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(
    reservations.router
    )

app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "SmartLimo AI API is running"}