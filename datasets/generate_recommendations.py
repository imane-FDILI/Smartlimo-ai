"""
SmartLimo AI - Générateur du dataset de recommandation de véhicule

Génère aléatoirement (mais de façon "métier-plausible") 2000 exemples
(passagers, bagages, occasion) -> véhicule recommandé, sauvegardés dans
vehicle_recommendation.csv. Ce dataset sert à entraîner le modèle de
train_recommender.py (arbre de décision).

NOTE : d'après l'analyse du reste du code, ce dataset et le modèle qui en
est issu ne sont actuellement pas utilisés en production - voir les
commentaires dans train_recommender.py et services/recommendation_service.py.
"""

import csv
import random

# La flotte reelle (capacites de ta table vehicles - a jour !)
FLEET = [
    {"name": "Sedan",         "capacity": 3,  "luggage": 3},
    {"name": "Executive SUV", "capacity": 6,  "luggage": 6},
    {"name": "Premium SUV",   "capacity": 6,  "luggage": 8},
    {"name": "Transit VAN",   "capacity": 14, "luggage": 14},
    {"name": "Sprinter VAN",  "capacity": 11, "luggage": 12},
]

OCCASIONS = ["airport", "wedding", "business", "party", "cruise", "other"]


def base_recommendation(passengers, luggage):
    # La meme logique que ta fonction recommend_vehicle :
    # le plus petit vehicule dont les capacites suffisent
    candidates = [v for v in FLEET if v["capacity"] >= passengers and v["luggage"] >= luggage]
    if not candidates:
        return None
    return min(candidates, key=lambda v: v["capacity"])["name"]


def generate_row():
    """Génère une ligne d'exemple plausible (passengers, luggage, occasion, vehicle).
    Retourne None si la combinaison passengers/luggage ne peut être servie
    par aucun véhicule de la flotte (auquel cas la ligne est ignorée par
    l'appelant plutôt que d'insérer une valeur invalide)."""
    # Un cas client plausible : plus souvent 1-4 passagers que 12 (comme en vrai !)
    # random.choices tire un nombre pondéré : les petites valeurs ont un
    # poids plus élevé, donc apparaissent plus fréquemment dans le dataset
    # généré, ce qui reflète la réalité (peu de groupes de 12-14 personnes).
    passengers = random.choices(
        population=[1, 2, 3, 4, 5, 6, 8, 10, 12, 14],
        weights=  [15, 25, 15, 12, 8, 8, 6, 5, 3, 3],   # les petits groupes dominent
    )[0]
    luggage = random.randint(0, passengers + 2)          # correle au nb de personnes
    occasion = random.choice(OCCASIONS)

    vehicle = base_recommendation(passengers, luggage)
    if vehicle is None:
        return None                                       # cas impossible -> saute

    # Le "bruit metier" : l'occasion influence le choix au-dela des capacites
    # mariage/business avec peu de monde -> on monte en gamme (le luxe compte !)
    # Ce "bruit" volontaire permet au modèle d'apprendre que l'occasion
    # compte aussi, pas seulement les capacités brutes (sinon la colonne
    # "occasion" n'aurait aucun pouvoir prédictif dans le dataset).
    if occasion in ("wedding", "business") and vehicle == "Sedan" and random.random() < 0.5:
        vehicle = "Executive SUV"
    if occasion == "wedding" and vehicle == "Executive SUV" and random.random() < 0.4:
        vehicle = "Premium SUV"

    return [passengers, luggage, occasion, vehicle]


with open("vehicle_recommendation.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["passengers", "luggage", "occasion", "vehicle"])   # l'en-tete
    count = 0
    while count < 2000:                                   # 2000 exemples
        row = generate_row()
        if row:
            writer.writerow(row)
            count += 1
        # si row est None (cas impossible), la boucle retente simplement
        # une nouvelle combinaison sans incrémenter count.

print(f"Dataset genere : {count} lignes -> vehicle_recommendation.csv")