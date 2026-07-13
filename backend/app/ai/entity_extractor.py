"""
SmartLimo AI - Entity extractor (NER)
Combine 3 approches :
  1. spaCy (en_core_web_sm)  -> dates, heures
  2. Gazetteer (entities.json) via PhraseMatcher -> lieux, véhicules, services
  3. Règles métier (regex)   -> passagers, bagages, pickup vs destination
"""

import json
import re
from pathlib import Path

import spacy
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

# --- chargement
BASE_DIR = Path(__file__).resolve().parents[2] # backend/
ENTITIES_PATH = BASE_DIR.parent / "datasets" / "entities.json"

nlp = spacy.load("en_core_web_sm")

with open(ENTITIES_PATH, encoding="utf-8") as f:
    GAZETTEER = json.load(f)

# Catégories du gazetteer -> label d'entité
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

# Construction du PhraseMatcher (insensible à la casse via LOWER)
matcher = PhraseMatcher(nlp.vocab, attr="LOWER")
CANONICAL = {}   # texte minuscule -> (label, nom canonique, catégorie)

for category, items in GAZETTEER.items():
    label = CATEGORY_LABELS.get(category)
    if not label:
        continue
    for item in items:
        terms = [item["name"]] + item.get("aliases", [])
        for term in terms:
            CANONICAL[term.lower()] = (label, item["name"], category)
        patterns = [nlp.make_doc(t) for t in terms]
        matcher.add(f"{label}::{item['name']}", patterns)

# règles regex
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "a couple of": 2,
}
NUM = r"(\d+|" + "|".join(WORD_NUMBERS) + r")"

PASSENGERS_RE = re.compile(
    NUM + r"\s*(passengers?|people|persons?|adults?|guests?|pax|of us|riders?)",
    re.IGNORECASE,
)
LUGGAGE_RE = re.compile(
    NUM + r"\s*(bags?|suitcases?|luggages?|pieces? of luggage|checked bags?)",
    re.IGNORECASE,
)
TIME_RE = re.compile(
    r"\b(\d{1,2})(:\d{2})?\s*(am|pm|a\.m\.|p\.m\.)\b|\b(\d{1,2}):(\d{2})\b",
    re.IGNORECASE,
)

PICKUP_PREPS = {"from", "at", "outside"}
DEST_PREPS = {"to", "into", "toward", "towards"}


def _to_number(value: str) -> int:
    value = value.lower().strip()
    return int(value) if value.isdigit() else WORD_NUMBERS.get(value, 0)


# -extraction
def extract_entities(text: str) -> dict:
    """Analyse un message et retourne les slots détectés."""
    doc = nlp(text)

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
    spans = [doc[s:e] for _, s, e in matcher(doc)]
    spans = filter_spans(spans)  # garde les correspondances les plus longues

    locations = []
    for span in spans:
        label, canonical, category = CANONICAL[span.text.lower()]
        if label == "LOCATION":
            locations.append((span, canonical, category))
        elif label == "VEHICLE" and not slots["vehicle"]:
            slots["vehicle"] = canonical
        elif label == "SERVICE" and not slots["service_type"]:
            slots["service_type"] = canonical
        elif label == "OCCASION" and not slots["occasion"]:
            slots["occasion"] = canonical
        elif label == "EXTRA" and canonical not in slots["extras"]:
            slots["extras"].append(canonical)

    # --- 2. Pickup vs destination selon la préposition qui précède
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
    if not slots["service_type"]:
        cat_of = {c for _, _, c in locations}
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
    for ent in doc.ents:
        if ent.label_ == "DATE" and not slots["date"]:
            slots["date"] = ent.text
        elif ent.label_ == "TIME" and not slots["time"]:
            slots["time"] = ent.text

    # Fallback regex pour l'heure ("2pm" parfois raté par spaCy)
    if not slots["time"]:
        m = TIME_RE.search(text)
        if m:
            slots["time"] = m.group(0)

    # Mots-clés date fréquents que spaCy peut classer ailleurs
    if not slots["date"]:
        for kw in ("tomorrow", "today", "tonight", "this weekend"):
            if kw in text.lower():
                slots["date"] = kw
                break

    # --- 5. Passagers et bagages (regex métier)
    m = PASSENGERS_RE.search(text)
    if m:
        slots["passengers"] = _to_number(m.group(1))
    m = LUGGAGE_RE.search(text)
    if m:
        slots["luggage"] = _to_number(m.group(1))

    return slots


# - test manuel
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