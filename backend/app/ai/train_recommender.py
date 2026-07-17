import pandas as pd
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.tree import DecisionTreeClassifier, export_text
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import accuracy_score, classification_report
import joblib

# 1. Charger le dataset (chemin complet = fiable)
df = pd.read_csv("C:/Projects/smartlimo/datasets/vehicle_recommendation.csv")
print(f"Dataset : {len(df)} lignes, {df['vehicle'].nunique()} vehicules")

# 2. Encoder l'occasion en nombres (les modeles ne mangent pas du texte)
occasion_encoder = LabelEncoder()
df["occasion_encoded"] = occasion_encoder.fit_transform(df["occasion"])

# 3. Features et cible
X = df[["passengers", "luggage", "occasion_encoded"]]
y = df["vehicle"]

# 4. Split 80/20 stratifie
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 5. L'arbre (max_depth contre le surapprentissage)
model = DecisionTreeClassifier(max_depth=6, random_state=42)
model.fit(X_train, y_train)

# 6. Evaluation
y_pred = model.predict(X_test)
print(f"Accuracy : {accuracy_score(y_test, y_pred):.2%}")
cv = cross_val_score(model, X, y, cv=5)
print(f"Cross-validation (5-fold) : {cv.mean():.2%} (+/- {cv.std()*2:.2%})")
print(classification_report(y_test, y_pred))

# 7. Les regles apprises par l'arbre !
print(export_text(model, feature_names=["passengers", "luggage", "occasion"]))

# 8. Sauvegarde du modele + de l'encodeur
joblib.dump(model, "app/ai/recommender_model.joblib")
joblib.dump(occasion_encoder, "app/ai/occasion_encoder.joblib")
print("Modele sauvegarde.")
