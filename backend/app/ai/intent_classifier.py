"""
SmartLimo AI - Intent classifier (inference)
Charge le modèle entraîné une seule fois et prédit l'intention
avec un score de confiance.
"""

from pathlib import Path

import joblib

MODEL_PATH = Path(__file__).resolve().parent / "intent_model.joblib"

# Chargé UNE fois au démarrage du serveur (pas à chaque requête)
_model = joblib.load(MODEL_PATH)

# Seuil de confiance : en dessous, on ne devine pas
CONFIDENCE_THRESHOLD = 0.30


def predict_intent(text: str) -> dict:
    """Retourne l'intention prédite et sa confiance."""
    probas = _model.predict_proba([text])[0]
    best_index = probas.argmax()
    intent = _model.classes_[best_index]
    confidence = float(probas[best_index])

    if confidence < CONFIDENCE_THRESHOLD:
        intent = "unknown"

    return {"intent": intent, "confidence": round(confidence, 3)}