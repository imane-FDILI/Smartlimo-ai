import requests   # la librairie pour appeler des APIs externes (pip install requests)

# En-tete obligatoire : Nominatim exige de s'identifier poliment
HEADERS = {"User-Agent": "SmartLimoAI/1.0 (stage project)"}


def geocode(place: str):
    # Transforme un nom de lieu en coordonnees GPS via Nominatim (OpenStreetMap)
    # Retourne (latitude, longitude) ou None si introuvable
    url = "https://nominatim.openstreetmap.org/search"
    params = {
        "q": f"{place}, Orlando, Florida",   # on ancre la recherche sur Orlando !
        "format": "json",
        "limit": 1,
    }
    resp = requests.get(url, params=params, headers=HEADERS, timeout=5)
    results = resp.json()                    # la reponse JSON -> liste Python
    if not results:
        return None
    return float(results[0]["lat"]), float(results[0]["lon"])


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
    resp = requests.get(url, params={"overview": "false"}, timeout=5)
    data = resp.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None

    route = data["routes"][0]
    return {
        "distance_km": round(route["distance"] / 1000, 1),   # metres -> km
        "duration_min": round(route["duration"] / 60),        # secondes -> minutes
        "pickup_coords": start,
        "dropoff_coords": end,
    }