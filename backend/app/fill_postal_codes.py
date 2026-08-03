from app.database import SessionLocal
from app.models import Zone, ZoneZipcode

POSTAL_CODES_BY_ZONE = {
    "DISNEY - LAKE B VISTA": ["32830", "32836", "32821"],
    "UNIVERSAL": ["32819"],
    "KISSIMMEE - SOUTH AREA": ["34741", "34742", "34743", "34744", "34745", "34746", "34747", "34758", "34759"],
    "DAVENPORT": ["33836", "33837", "33896", "33897"],
    "LEGOLAND": ["33884"],
    "PORT": ["32920", "32931", "32932"],
}


def run():
    db = SessionLocal()
    try:
        for zone_code, postal_codes in POSTAL_CODES_BY_ZONE.items():
            zone = db.query(Zone).filter(Zone.code == zone_code).first()
            if zone is None:
                print(f"Zone {zone_code} introuvable, ignoree.")
                continue
            db.query(ZoneZipcode).filter(ZoneZipcode.zone_id == zone.id).delete()
            for zipcode in postal_codes:
                db.add(ZoneZipcode(zone_id=zone.id, zipcode=zipcode))
            print(f"{zone_code} : {len(postal_codes)} codes postaux ajoutes.")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    run()