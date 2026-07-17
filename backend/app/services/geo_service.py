import requests   # la librairie pour appeler des APIs externes (pip install requests)

from app.ai.entity_extractor import resolve_location

# En-tete obligatoire : Nominatim exige de s'identifier poliment
HEADERS = {"User-Agent": "SmartLimoAI/1.0 (stage project)"}


def geocode(place: str):
    # Transforme un nom de lieu en coordonnees GPS via Nominatim (OpenStreetMap)
    # Retourne (latitude, longitude) ou None si introuvable
    place = place.strip().strip(".")
    place = resolve_location(place)   # corrige les fautes de frappe via le gazetteer
    url = "https://nominatim.openstreetmap.org/search"
    # 1ere tentative : le lieu tel quel (deja precis pour les noms du gazetteer,
    # ex: "Miami International Airport"). 2eme tentative : on ajoute la region
    # pour desambiguiser les adresses generiques (ex: "the airport").
    for query in (place, f"{place}, Florida, USA"):
        params = {"q": query, "format": "json", "limit": 1}
        resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
        results = resp.json()                    # la reponse JSON -> liste Python
        if results:
            return float(results[0]["lat"]), float(results[0]["lon"])
    return None


def get_route(pickup: str, dropoff: str):
    # Calcule le trajet entre deux lieux via OSRM (routing OpenStreetMap)
    # Retourne un dict {distance_km, duration_min, pickup_coords, dropoff_coords}
    # ou None si un des lieux est introuvable
    start = geocode(pickup)
    end = geocode(dropoff)
    if start is None or end is None:
        return None

    # OSRM attend lon,lat (attention : inverse de l'habitude !)
    url = f"https://router.project-osrm.org/route/v1/driving/{start[1]},{start[0]};{end[1]},{end[0]}"
    resp = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=5)
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "distance_km": round(route["distance"] / 1000, 1),   # metres -> km
        "duration_min": round(route["duration"] / 60),        # secondes -> minutes
        "pickup_coords": start,
        "dropoff_coords": end,
        "geometry": [[p[1], p[0]] for p in route["geometry"]["coordinates"]],
    }