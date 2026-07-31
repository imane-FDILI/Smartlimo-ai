"""
SmartLimo AI - Intent classifier training
Pipeline : TF-IDF (unigrams + bigrams) -> Logistic Regression
Usage : python -m app.ai.train_intents  (depuis le dossier backend)

Ce script est exécuté manuellement (hors ligne), séparément du serveur
FastAPI : il entraîne le modèle de classification d'intentions à partir
d'un dataset annoté (datasets/intents.csv) et sauvegarde le résultat dans
intent_model.joblib, qui sera ensuite chargé par intent_classifier.py au
démarrage de l'API.
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.pipeline import Pipeline


# Chemins
# BASE_DIR remonte de 2 niveaux (backend/app/ai/ -> backend/) pour pouvoir
# localiser le dossier "datasets" au même niveau que "backend".
BASE_DIR = Path(__file__).resolve().parents[2]
DATASET_PATH = BASE_DIR.parent / "datasets" / "intents.csv"
# Le modèle entraîné est sauvegardé à côté de ce script, dans le même
# dossier que celui lu par intent_classifier.py (backend/app/ai/).
MODEL_PATH = Path(__file__).resolve().parent / "intent_model.joblib"


def main():
    """Entraîne, évalue et sauvegarde le modèle de classification d'intentions.

    Le dataset (intents.csv) doit contenir au minimum deux colonnes :
      - "text"   : la phrase de l'utilisateur
      - "intent" : l'intention correspondante (label à prédire)
    """
    # 1. Charger le dataset
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset : {len(df)} phrases, {df['intent'].nunique()} intentions")

    X = df["text"]
    y = df["intent"]

    # 2. Split train/test (stratifié pour garder l'équilibre des classes)
    # `stratify=y` garantit que chaque intention est représentée dans les
    # mêmes proportions dans le jeu d'entraînement et le jeu de test.
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train : {len(X_train)} | Test : {len(X_test)}")
    # Cross-validation 5-fold (mesure plus fiable que le simple split) :
    # on entraîne/teste le pipeline 5 fois sur des découpages différents du
    # dataset complet pour obtenir une estimation moins dépendante d'un
    # split particulier. Ce pipeline de cross-validation est temporaire
    # (recréé ici) et distinct de celui réellement entraîné et sauvegardé
    # plus bas.
    cv_scores = cross_val_score(
        Pipeline([
            ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=10)),
        ]),
        X, y, cv=5
    )
    print(f"Cross-validation (5-fold) : {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

    # 3. Pipeline TF-IDF + Logistic Regression
    # TF-IDF transforme chaque phrase en vecteur numérique basé sur la
    # fréquence des mots (et paires de mots) qu'elle contient, pondérée par
    # leur rareté dans l'ensemble du dataset. La régression logistique
    # apprend ensuite à séparer les intentions à partir de ces vecteurs.
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),      # unigrammes + bigrammes ("book a", "my driver")
            sublinear_tf=True,       # atténue l'effet des mots très répétés (log(1+tf))
        )),
        ("clf", LogisticRegression(
            max_iter=1000,           # nombre d'itérations max pour la convergence
            C=10,                    # inverse de la régularisation (plus C est grand, moins on régularise)
        )),
    ])

    # 4. Entraînement sur le jeu d'entraînement uniquement
    pipeline.fit(X_train, y_train)

    # 5. Évaluation sur le jeu de test (jamais vu pendant l'entraînement)
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy : {acc:.2%}\n")
    # classification_report détaille précision/rappel/f1-score par intention,
    # utile pour repérer les intentions mal apprises (peu d'exemples, ambiguës...).
    print(classification_report(y_test, y_pred))

    # 6. Sauvegarde du modèle final (ré-entraîné implicitement sur X_train
    # seulement à l'étape 4 -- pas sur l'intégralité du dataset).
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Modele sauvegarde : {MODEL_PATH}")

    # 7. Petit test manuel : quelques phrases "à la main" pour vérifier
    # rapidement, à l'œil, que les prédictions ont du sens.
    examples = [
        "I need a limo tomorrow at 3pm",
        "where is my driver",
        "how much to disney world",
        "yes confirm it",
        "can I pay with apple pay",
    ]
    print("\n--- Test manuel ---")
    for text in examples:
        print(f"  '{text}' -> {pipeline.predict([text])[0]}")


if __name__ == "__main__":
    main()