"""
SmartLimo AI - Entity extractor (NER)
Combine 3 approches :
  1. spaCy (en_core_web_sm)  -> dates, heures
  2. Gazetteer (entities.json) via PhraseMatcher -> lieux, véhicules, services
  3. Règles métier (regex)   -> passagers, bagages, pickup vs destination
"""

import json
import re
from difflib import get_close_matches
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

# --- chargement --------------------------------------------------------
# BASE_DIR remonte de 2 niveaux depuis ce fichier (backend/app/ai/ -> backend/)
# afin de pouvoir localiser le dossier "datasets" qui se trouve au même
# niveau que "backend" dans l'arborescence du projet.
BASE_DIR = Path(__file__).resolve().parents[2]  # backend/
ENTITIES_PATH = BASE_DIR.parent / "datasets" / "entities.json"

# Modèle spaCy anglais "petit" : suffisant pour détecter dates/heures (DATE, TIME)
# sans avoir besoin d'un modèle plus lourd.
nlp = spacy.load("en_core_web_sm")

# Le gazetteer est un dictionnaire JSON qui liste, par catégorie
# (aéroports, ports, hôtels, véhicules, services...), les noms officiels
# et leurs alias/variantes possibles (ex: "MCO" comme alias d'un aéroport).
with open(ENTITIES_PATH, encoding="utf-8") as f:
    GAZETTEER = json.load(f)

# Fait correspondre chaque catégorie du gazetteer au label d'entité NER
# qu'on veut lui attribuer lors de la détection.
CATEGORY_LABELS = {
    "airports": "LOCATION",
    "ports": "LOCATION",
    "theme_parks": "LOCATION",
    "hotels": "LOCATION",
    "places": "LOCATION",
    "vehicle_types": "VEHICLE",
    "service_types": "SERVICE",
    "occasions": "OCCASION",
    "extras": "EXTRA",
}

# Construction du PhraseMatcher (insensible à la casse via l'attribut LOWER).
# Le PhraseMatcher permet de repérer directement dans le texte des suites de
# mots exactes (ex: "Orlando International Airport") sans avoir à écrire
# de regex, ce qui est beaucoup plus rapide et fiable qu'une recherche de
# sous-chaîne pour une longue liste de noms propres.
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

# Dictionnaire de correspondance inverse : texte en minuscule -> (label, nom canonique, catégorie).
# Sert à la fois à retrouver rapidement l'entité associée à un span détecté
# par le PhraseMatcher, et à la correction de fautes de frappe (resolve_location).
CANONICAL = {}

for category, items in GAZETTEER.items():
    label = CATEGORY_LABELS.get(category)
    if not label:
        # Catégorie inconnue dans CATEGORY_LABELS : on l'ignore simplement.
        continue
    for item in items:
        # On indexe à la fois le nom officiel ET tous ses alias, pour que
        # l'utilisateur puisse écrire "MCO" ou "Orlando International Airport"
        # et que les deux soient reconnus comme la même entité.
        terms = [item["name"]] + item.get("aliases", [])
        for term in terms:
            CANONICAL[term.lower()] = (label, item["name"], category)
        # Chaque terme (nom + alias) devient un motif de recherche pour le matcher.
        patterns = [nlp.make_doc(t) for t in terms]
        matcher.add(f"{label}::{item['name']}", patterns)


def resolve_location(text: str) -> str:
    """Corrige les petites fautes de frappe dans un nom de lieu en le comparant
    au gazetteer (ex: 'Orlando interntional airport' -> 'Orlando International Airport').
    Retourne le texte original si aucune correspondance suffisamment proche n'est trouvee."""
    key = text.strip().lower()
    # 1er essai : correspondance exacte (rapide, cas le plus fréquent).
    if key in CANONICAL:
        return CANONICAL[key][1]
    # 2e essai : recherche de la chaîne la plus proche (tolère les fautes de frappe).
    # cutoff=0.82 = seuil de similarité minimum (0 à 1) pour accepter une correspondance.
    match = get_close_matches(key, CANONICAL.keys(), n=1, cutoff=0.82)
    if match and CANONICAL[match[0]][0] == "LOCATION":
        return CANONICAL[match[0]][1]
    # Aucune correspondance fiable trouvée : on renvoie le texte tel quel.
    return text


# ------------------------------------------------------------------------
# Règles métier basées sur des expressions régulières (regex).
# Ces règles complètent le gazetteer et spaCy pour extraire des informations
# qui ne sont pas des "entités nommées" classiques : nombre de passagers,
# nombre de bagages, heure au format "2pm", etc.
# ------------------------------------------------------------------------

# Permet de convertir les nombres écrits en toutes lettres (ex: "three" -> 3)
# en plus des chiffres classiques.
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "a couple of": 2,
}
# Motif regex représentant "un nombre" : soit des chiffres (\d+), soit un des
# mots de WORD_NUMBERS (construit dynamiquement à partir de ses clés).
NUM = r"(\d+|" + "|".join(WORD_NUMBERS) + r")"

# Détecte des expressions comme "4 passengers", "3 people", "a couple of us"...
PASSENGERS_RE = re.compile(
    NUM + r"\s*(passengers?|people|persons?|adults?|guests?|pax|of us|riders?)",
    re.IGNORECASE,
)
# Détecte des expressions comme "5 bags", "2 suitcases", "3 pieces of luggage"...
LUGGAGE_RE = re.compile(
    NUM + r"\s*(bags?|suitcases?|luggages?|pieces? of luggage|checked bags?)",
    re.IGNORECASE,
)
# Détecte une heure au format "2pm", "2:30 pm", "14:30"... utilisé en secours
# quand spaCy ne détecte pas l'heure comme entité TIME.
TIME_RE = re.compile(
    r"\b(\d{1,2})(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b|\b(\d{1,2}):(\d{2})\b",
    re.IGNORECASE,
)

# Prépositions anglaises qui précèdent généralement un lieu de départ (pickup)
# vs un lieu d'arrivée (destination). Utilisées pour désambiguïser quand
# plusieurs lieux sont mentionnés dans la même phrase.
PICKUP_PREPS = {"from", "at", "outside"}
DEST_PREPS = {"to", "into", "toward", "towards"}


def _to_number(value: str) -> int:
    """Convertit une chaîne représentant un nombre (chiffres ou mot anglais)
    en entier. Retourne 0 si la valeur n'est pas reconnue (cas normalement
    impossible car `value` provient toujours d'un match des regex ci-dessus)."""
    value = value.lower().strip()
    return int(value) if value.isdigit() else WORD_NUMBERS.get(value, 0)


# ------------------------------------------------------------------------
# Fonction principale d'extraction
# ------------------------------------------------------------------------
def extract_entities(text: str) -> dict:
    """Analyse un message et retourne les slots détectés."""
    # Le texte est d'abord passé dans le pipeline spaCy (tokenisation,
    # reconnaissance d'entités DATE/TIME natives, etc.).
    doc = nlp(text)

    # Structure de sortie : un "slot" par information que le chatbot a besoin
    # de collecter pour faire une réservation. Toutes les valeurs démarrent
    # à None (ou liste vide pour "extras") et sont remplies au fur et à mesure.
    slots = {
        "pickup_location": None,
        "dropoff_location": None,
        "date": None,
        "time": None,
        "passengers": None,
        "luggage": None,
        "vehicle": None,
        "service_type": None,
        "occasion": None,
        "extras": [],
    }

    # --- 1. Gazetteer : lieux, véhicules, services, occasions, extras
    # Le PhraseMatcher retourne des tuples (match_id, start, end) : on les
    # convertit en spans (segments de texte) pour pouvoir les manipuler.
    spans = [doc[s:e] for _, s, e in matcher(doc)]
    # filter_spans() supprime les chevauchements en gardant la correspondance
    # la plus longue (ex: si "Orlando" ET "Orlando International Airport"
    # matchent tous les deux, on garde seulement la version complète).
    spans = filter_spans(spans)

    locations = []
    for span in spans:
        label, canonical, category = CANONICAL[span.text.lower()]
        if label == "LOCATION":
            # Les lieux sont mis de côté : on décidera pickup vs dropoff
            # dans l'étape suivante, car un lieu seul ne suffit pas à savoir
            # s'il s'agit du point de départ ou de la destination.
            locations.append((span, canonical, category))
        elif label == "" and not slots["vehicle"]:
            # NOTE: ce label vaut toujours "VEHICLE" d'après CATEGORY_LABELS
            # (jamais une chaîne vide) : cette branche ne s'exécute donc
            # jamais en pratique et le slot "vehicle" n'est actuellement
            # jamais rempli par le gazetteer. À vérifier/corriger si le
            # type de véhicule doit être détecté ici.
            slots["vehicle"] = canonical
        elif label == "SERVICE" and not slots["service_type"]:
            slots["service_type"] = canonical
        elif label == "OCCASION" and not slots["occasion"]:
            slots["occasion"] = canonical
        elif label == "EXTRA" and canonical not in slots["extras"]:
            # Les extras sont cumulatifs (plusieurs options possibles),
            # contrairement aux autres slots qui n'acceptent qu'une valeur.
            slots["extras"].append(canonical)

    # --- 2. Pickup vs destination selon la préposition qui précède
    # Pour chaque lieu détecté, on regarde le mot juste avant dans la phrase :
    # "from <lieu>" => pickup, "to <lieu>" => destination. Si la préposition
    # n'est pas reconnue, on remplit les slots dans l'ordre d'apparition
    # (le premier lieu devient pickup, le second devient dropoff).
    for span, canonical, category in locations:
        prev = doc[span.start - 1].lower_ if span.start > 0 else ""
        if prev in PICKUP_PREPS and not slots["pickup_location"]:
            slots["pickup_location"] = canonical
        elif prev in DEST_PREPS and not slots["dropoff_location"]:
            slots["dropoff_location"] = canonical
        elif not slots["pickup_location"]:
            slots["pickup_location"] = canonical
        elif not slots["dropoff_location"]:
            slots["dropoff_location"] = canonical

    # --- 3. Déduction du service_type depuis les lieux (si non explicite)
    # Si l'utilisateur n'a pas dit explicitement le type de service
    # (ex: "airport transfer"), on essaie de le déduire de la catégorie
    # des lieux détectés : un trajet vers/depuis un aéroport ou un port
    # implique un service_type particulier.
    if not slots["service_type"]:
        cat_of = {c for _, _, c in locations}  # (variable non utilisée ensuite, conservée telle quelle)
        pickup_cat = next((c for _, n, c in locations if n == slots["pickup_location"]), None)
        drop_cat = next((c for _, n, c in locations if n == slots["dropoff_location"]), None)
        if pickup_cat == "airports":
            slots["service_type"] = "from_airport"
        elif drop_cat == "airports":
            slots["service_type"] = "to_airport"
        elif pickup_cat == "ports":
            slots["service_type"] = "from_port"
        elif drop_cat == "ports":
            slots["service_type"] = "to_port"

    # --- 4. spaCy : dates et heures
    # On parcourt les entités nommées détectées nativement par spaCy et on
    # récupère la première DATE et la première TIME rencontrées.
    for ent in doc.ents:
        if ent.label_ == "DATE" and not slots["date"]:
            slots["date"] = ent.text
        elif ent.label_ == "TIME" and not slots["time"]:
            slots["time"] = ent.text

    # Fallback regex pour l'heure ("2pm" parfois raté par spaCy) : si spaCy
    # n'a rien trouvé, on retente avec notre propre regex plus permissive.
    if not slots["time"]:
        m = TIME_RE.search(text)
        if m:
            slots["time"] = m.group(0)

    # Mots-clés date fréquents que spaCy peut classer ailleurs (ou ignorer) :
    # on les cherche en texte brut si aucune DATE n'a encore été trouvée.
    if not slots["date"]:
        for kw in ("tomorrow", "today", "tonight", "this weekend"):
            if kw in text.lower():
                slots["date"] = kw
                break

    # --- 5. Passagers et bagages (regex métier)
    # Ces informations ne sont jamais des "entités nommées" au sens spaCy,
    # elles sont donc entièrement extraites via nos regex métier.
    m = PASSENGERS_RE.search(text)
    if m:
        slots["passengers"] = _to_number(m.group(1))
    m = LUGGAGE_RE.search(text)
    if m:
        slots["luggage"] = _to_number(m.group(1))

    return slots


# ------------------------------------------------------------------------
# Test manuel : exécuter ce fichier directement (`python entity_extractor.py`)
# affiche, pour chaque phrase d'exemple, les slots détectés (en ignorant
# ceux qui sont restés vides/None) afin de vérifier rapidement le
# comportement de l'extracteur sans passer par l'API.
# ------------------------------------------------------------------------
if __name__ == "__main__":
    tests = [
        "I need a limo tomorrow at 2 PM from MCO to Disney World for 4 people with 5 suitcases",
        "Book a Sprinter from the Hilton Orlando to Port Canaveral next Friday",
        "We are 8 people going to a wedding, pick us up at 6pm",
        "How much from Sanford airport to Universal Studios?",
        "I want an SUV to the airport tonight, 3 passengers and a child seat",
    ]
    for t in tests:
        print(f"\n>>> {t}")
        for k, v in extract_entities(t).items():
            if v not in (None, []):
                print(f"    {k:18s} = {v}")
