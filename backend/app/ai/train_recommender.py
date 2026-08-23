"""
SmartLimo AI - Entraînement du modèle de recommandation de véhicule

Ce script entraîne un arbre de décision qui, à partir du nombre de
passagers, du nombre de bagages et de l'occasion du trajet (mariage,
aéroport, tourisme...), prédit le véhicule le plus adapté dans la flotte.

NOTE IMPORTANTE : à ce jour, le modèle et l'encodeur sauvegardés ici
(recommender_model.joblib / occasion_encoder.joblib) ne sont chargés/
utilisés par aucun autre fichier du projet. La recommandation utilisée en
production par le chatbot passe par la fonction recommend_vehicle de
app/services/reservation_service.py, qui est une règle simple (le plus
petit véhicule dont la capacité suffit) et non ce modèle entraîné. Ce
script semble donc être une expérimentation/ébauche pas encore branchée
au reste de l'application (voir aussi services/recommendation_service.py
qui contient une fonction recommend_vehicle du même nom, elle aussi inutilisée).

Usage : python app/ai/train_recommender.py (depuis le dossier backend),
ou directement via python train_recommender.py si les chemins de sauvegarde
relatifs ("app/ai/...") sont exécutés depuis backend/.
"""

import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib

# 1. Charger le dataset (chemin complet = fiable)
# Chemin absolu utilisé volontairement pour éviter les erreurs liées au
# répertoire courant depuis lequel le script est lancé.
df = pd.read_csv("C:/Projects/smartlimo/datasets/vehicle_recommendation.csv")
print(f"Dataset : {len(df)} lignes, {df['vehicle'].nunique()} vehicules")

# 2. Encoder l'occasion en nombres (les modeles ne mangent pas du texte)
# LabelEncoder transforme chaque valeur textuelle unique de la colonne
# "occasion" (ex: "wedding", "airport", "tourism") en un entier distinct,
# nécessaire car DecisionTreeClassifier ne travaille qu'avec des nombres.
occasion_encoder = LabelEncoder()
df["occasion_encoded"] = occasion_encoder.fit_transform(df["occasion"])

# 3. Features et cible
# Les 3 variables d'entrée (features) utilisées pour prédire le véhicule
# (la cible/target `y`) à recommander.
X = df[["passengers", "luggage", "occasion_encoded"]]
y = df["vehicle"]

# 4. Split 80/20 stratifie
# `stratify=y` garantit que chaque type de véhicule est représenté dans
# les mêmes proportions à l'entraînement et au test.
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 5. L'arbre (max_depth contre le surapprentissage)
# Un arbre de décision est utilisé plutôt qu'un modèle plus complexe car
# il est facilement interprétable (voir export_text plus bas) et les
# règles de recommandation sont naturellement des règles de type
# "si passagers > X et bagages > Y alors véhicule Z". max_depth=6 limite
# la profondeur de l'arbre pour éviter qu'il ne mémorise le dataset
# d'entraînement au lieu d'apprendre des règles générales.
model = DecisionTreeClassifier(max_depth=6, random_state=42)
model.fit(X_train, y_train)

# 6. Evaluation
y_pred = model.predict(X_test)
print(f"Accuracy : {accuracy_score(y_test, y_pred):.2%}")
# Cross-validation 5-fold : donne une estimation de la performance plus
# robuste qu'un seul split train/test.
cv = cross_val_score(model, X, y, cv=5)
print(f"Cross-validation (5-fold) : {cv.mean():.2%} (+/- {cv.std()*2:.2%})")
print(classification_report(y_test, y_pred))

# 7. Les regles apprises par l'arbre !
# export_text affiche l'arbre sous forme de texte lisible (une suite de
# conditions if/else), ce qui permet de vérifier "à l'œil" que les règles
# apprises ont du sens métier (ex: beaucoup de passagers -> van).
print(export_text(model, feature_names=["passengers", "luggage", "occasion"]))

# 8. Sauvegarde du modele + de l'encodeur
# L'encodeur doit être sauvegardé en plus du modèle car il faudra
# ré-encoder l'occasion de la même façon lors des prédictions en
# production (recommendation_service.py charge les deux fichiers).
joblib.dump(model, "app/ai/recommender_model.joblib")
joblib.dump(occasion_encoder, "app/ai/occasion_encoder.joblib")
print("Modele sauvegarde.")
