"""
SmartLimo AI - Intent classifier (inference)
Charge le modèle entraîné une seule fois et prédit l'intention
avec un score de confiance.

Le modèle lui-même (pipeline scikit-learn : vectorisation du texte +
classifieur) est entraîné séparément par train_intents.py et sauvegardé
au format .joblib. Ce module ne fait que charger ce fichier et l'utiliser
pour prédire, il ne contient aucune logique d'entraînement.
"""

from pathlib import Path

import joblib

# Chemin du modèle entraîné : toujours dans le même dossier que ce fichier
# (backend/app/ai/intent_model.joblib), généré par train_intents.py.
MODEL_PATH = Path(__file__).resolve().parent / "intent_model.joblib"

# Chargé UNE fois au démarrage du serveur (pas à chaque requête) : charger
# un modèle depuis le disque est coûteux, il ne faut donc surtout pas le
# refaire à chaque appel de predict_intent().
_model = joblib.load(MODEL_PATH)

# Seuil de confiance : en dessous, on ne devine pas. Si la meilleure
# probabilité prédite par le modèle est trop faible, on préfère renvoyer
# "unknown" plutôt qu'une intention peu fiable, pour éviter que le
# dialogue manager ne parte dans une mauvaise direction.
CONFIDENCE_THRESHOLD = 0.30


def predict_intent(text: str) -> dict:
    """Retourne l'intention prédite et sa confiance.

    `predict_proba` renvoie, pour un texte donné, la probabilité estimée
    pour CHAQUE intention possible (une liste de scores qui somment à 1).
    On prend ici l'intention dont la probabilité est la plus élevée.
    """
    # predict_proba attend une liste de textes (même pour un seul texte),
    # d'où le `[text]` et le `[0]` pour récupérer le résultat du premier
    # (et unique) élément.
    probas = _model.predict_proba([text])[0]
    best_index = probas.argmax()               # index de la probabilité la plus haute
    intent = _model.classes_[best_index]        # nom de l'intention correspondante
    confidence = float(probas[best_index])       # sa probabilité (0 à 1)

    if confidence < CONFIDENCE_THRESHOLD:
        # Prédiction trop incertaine : on préfère l'admettre plutôt que
        # de risquer une mauvaise interprétation du message utilisateur.
        intent = "unknown"

    return {"intent": intent, "confidence": round(confidence, 3)}