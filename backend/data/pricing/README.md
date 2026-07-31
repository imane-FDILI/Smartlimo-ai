# Grille de tarifs fixes

Fichiers Excel sources, lus par `app.import_pricing`
(`python -m app.import_pricing` depuis `backend/`) :

- `TEMPLATE_Zones.xlsx` — colonnes :
  `Zone Code | Zone Description | Cities in Zone | Postal Codes | State`
- `TEMPLATE_Rates.xlsx` — grille zone-à-zone, colonnes :
  `Vehicle Code | Zone From (Code) | Zone To (Code) | Rate | Tolls | Parking | Tax 1 | Tax 2 | Matrix | Is Default Matrix`
- `TEMPLATE_HourlyRates.xlsx` — tarifs à l'heure, colonnes :
  `Vehicle Code | Hourly Rate | Minimum Hours | Notice Hours`
- `TEMPLATE_Surcharges.xlsx` — suppléments et frais annexes, colonnes :
  `Code | Label | Amount | Percent | Description`
- `TEMPLATE_WaitTime.xlsx` — grace period / temps d'attente, colonnes :
  `Trip Type | Grace Period Minutes | Increment Minutes | Rate Per Increment`

Données actuelles issues du rate card Example Limousine (PDF).
Le référentiel de véhicules de `TEMPLATE_Rates.xlsx` (SEDAN/SUV/VAN/SPRINTER VAN/LIMOUSINE)
est distinct de celui de `TEMPLATE_HourlyRates.xlsx` (9 catégories, ex: PREMIUM SEDAN,
SPRINTER EXECUTIVE, PARTY BUS...) : ce sont deux découpages différents dans le
document source, pas encore réconciliés avec `Vehicle.name` (flotte NLP).

Ces fichiers ne sont pas versionnés (voir `.gitignore`).
