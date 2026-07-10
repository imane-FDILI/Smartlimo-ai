"""
SmartLimo AI - Intent classifier training
Pipeline : TF-IDF (unigrams + bigrams) -> Logistic Regression
Usage : python -m app.ai.train_intents  (depuis le dossier backend)
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
BASE_DIR = Path(__file__).resolve().parents[2]          
DATASET_PATH = BASE_DIR.parent / "datasets" / "intents.csv"
MODEL_PATH = Path(__file__).resolve().parent / "intent_model.joblib"


def main():
    # 1. Charger le dataset
    df = pd.read_csv(DATASET_PATH)
    print(f"Dataset : {len(df)} phrases, {df['intent'].nunique()} intentions")

    X = df["text"]
    y = df["intent"]

    # 2. Split train/test (stratifié pour garder l'équilibre des classes)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"Train : {len(X_train)} | Test : {len(X_test)}")
    # Cross-validation 5-fold (mesure plus fiable que le simple split)
    cv_scores = cross_val_score(
        Pipeline([
            ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2), sublinear_tf=True)),
            ("clf", LogisticRegression(max_iter=1000, C=10)),
        ]),
        X, y, cv=5
    )
    print(f"Cross-validation (5-fold) : {cv_scores.mean():.2%} (+/- {cv_scores.std():.2%})")

    # 3. Pipeline TF-IDF + Logistic Regression
    pipeline = Pipeline([
        ("tfidf", TfidfVectorizer(
            lowercase=True,
            ngram_range=(1, 2),      # unigrammes + bigrammes ("book a", "my driver")
            sublinear_tf=True,
        )),
        ("clf", LogisticRegression(
            max_iter=1000,
            C=10,
        )),
    ])

    # 4. Entraînement
    pipeline.fit(X_train, y_train)

    # 5. Évaluation
    y_pred = pipeline.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy : {acc:.2%}\n")
    print(classification_report(y_test, y_pred))

    # 6. Sauvegarde du modèle
    joblib.dump(pipeline, MODEL_PATH)
    print(f"Modele sauvegarde : {MODEL_PATH}")

    # 7. Petit test manuel
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