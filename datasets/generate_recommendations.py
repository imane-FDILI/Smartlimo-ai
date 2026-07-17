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
    # Un cas client plausible : plus souvent 1-4 passagers que 12 (comme en vrai !)
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

print(f"Dataset genere : {count} lignes -> vehicle_recommendation.csv")