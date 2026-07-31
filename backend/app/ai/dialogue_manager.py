"""
SmartLimo AI - Gestionnaire de dialogue (dialogue manager)

Ce module est le "cerveau" du chatbot : il reçoit un message utilisateur,
détecte son intention (via intent_classifier) et les entités qu'il contient
(via entity_extractor), puis décide de la réponse à donner en fonction de
l'état de la conversation (session).

La conversation est modélisée comme une petite machine à états :
  - "idle"       : aucune réservation en cours
  - "collecting" : on est en train de collecter les informations (slots)
                   nécessaires à la réservation (lieu, date, véhicule...)
  - "confirming" : tous les slots sont remplis, on attend la confirmation
                   finale de l'utilisateur avant de créer la réservation
  - "completed"  : la réservation a été créée

En plus de ce flux principal de réservation, le module gère aussi des
sous-dialogues plus courts (demande de prix, historique des trajets,
modification/annulation de réservation, etc.) via le champ `expected`
qui indique quelle information précise on attend dans le prochain message.
"""

import re
import uuid

from app.ai.intent_classifier import predict_intent
from app.ai.entity_extractor import extract_entities

SESSIONS = {}

REQUIRED_SLOTS = [
    ("pickup_location", "Where would you like to be picked up?"),
    ("dropoff_location", "What is your destination?"),
    ("date", "What date would you like to travel?"),
    ("time", "What time would you like to be picked up?"),
    ("passengers", "How many passengers will be traveling?"),
    ("luggage", "How many pieces of luggage will you have?"),
    ("vehicle", "What type of vehicle would you prefer? "),
    ("name", "Great! May I have your full name?"),
    ("phone", "Could you provide your phone number?"),
    ("email", "And your email address?"),
]

SLOT_LABELS = {
    "pickup_location": "Pickup", "dropoff_location": "Destination",
    "date": "Date", "time": "Time", "passengers": "Passengers",
    "luggage": "Luggage", "vehicle": "Vehicle", "name": "Name",
    "phone": "Phone", "email": "Email",
}

EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{6,}\d")
NUM_RE = re.compile(r"\d+")
NO_PREF_RE = re.compile(r"no preference|any|whatever|doesn'?t matter", re.I)
ACCEPT_RECO_RE = re.compile(r"\b(yes|sure|ok|okay|sounds good|your recommendation|that one|the one you suggested|agree)\b", re.I)
NONE_RE = re.compile(r"\b(none|no|zero|nothing)\b", re.I)
RESERVATION_NUM_RE = re.compile(r"#?(\d+)")

# Mots-clés reconnus pour identifier quel slot l'utilisateur veut modifier
# après avoir refusé (deny) le résumé de réservation (voir "edit_field"
# dans handle_message). Recherche par mot entier (\b), premier match gagne.
EDIT_FIELD_KEYWORDS = {
    "pickup_location": ["pickup", "pick up", "pick-up"],
    "dropoff_location": ["destination", "dropoff", "drop off", "drop-off"],
    "date": ["date"],
    "time": ["time"],
    "passengers": ["passenger", "passengers"],
    "luggage": ["luggage", "bag", "bags"],
    "vehicle": ["vehicle", "car"],
    "name": ["name"],
    "phone": ["phone", "number"],
    "email": ["email"],
}

INTENT_RESPONSES = {
    "greeting": "Hello! Welcome to SmartLimo AI. I can help you book a limousine, get a price estimate, or track your driver. How can I help you today?",
    "cancel_booking": "I can help you cancel your reservation. Could you give me your booking details?",
    "modify_booking": "Sure, let's update your reservation. What would you like to change?",
    "driver_tracking": "Let me check your driver's location. Could you give me your booking reference?",
    "trip_history": "Here's where I'd show your past rides. (Coming soon!)",
    "payment": "We accept credit cards, cash, and online payments. What would you like to know?",
    "tip": "You can add a tip for your driver at any time. Would you like to add one?",
    "pricing": "I can give you a price estimate. Where are you traveling from and to?",
    "vehicle_information": "Our fleet includes Sedans, Executive SUVs, Premium SUVs, Transit VANs and Sprinter VANs. What would you like to know?",
    "help": "I can help you: book a ride, get a price, track your driver, or manage your reservations. Just tell me what you need!",
    "thanks": "You're very welcome! Anything else I can do for you?",
    "goodbye": "Thank you for choosing SmartLimo! Have a wonderful day!",
    "unknown": "I'm sorry, I didn't quite understand that. I can help you book a ride, get a price, or track your driver.",
}


def _new_session():
    return {"slots": {}, "stage": "idle", "expected": None, "reservation_id": None}


def _merge_entities(slots: dict, entities: dict):
    captured = []
    for key in ("pickup_location", "dropoff_location", "date", "time",
                "passengers", "luggage", "vehicle", "service_type", "occasion"):
        if entities.get(key) not in (None, []) and not slots.get(key):
            slots[key] = entities[key]
            if key in SLOT_LABELS:
                captured.append(key)
    if entities.get("extras"):
        slots.setdefault("extras", [])
        for e in entities["extras"]:
            if e not in slots["extras"]:
                slots["extras"].append(e)
    return captured


def _scan_contact_info(slots: dict, message: str):
    if not slots.get("email"):
        m = EMAIL_RE.search(message)
        if m:
            slots["email"] = m.group()
    if not slots.get("phone"):
        m = PHONE_RE.search(message)
        if m:
            slots["phone"] = m.group()


def _format_name(raw: str) -> str:
    parts = raw.strip().split()
    if len(parts) < 2:
        return raw.strip().capitalize()
    first = parts[0].capitalize()
    last = " ".join(p.upper() for p in parts[1:])
    return f"{first} {last}"


def _fill_expected(slots: dict, expected: str, message: str) -> bool:
    text = message.strip().strip(".")
    if not expected or slots.get(expected):
        return False
    if expected in ("passengers", "luggage"):
        if NONE_RE.search(text):
            slots[expected] = 0
            return True
        m = NUM_RE.search(text)
        if m:
            slots[expected] = int(m.group())
            return True
    elif expected == "vehicle":
        if NO_PREF_RE.search(text):
            slots[expected] = "No Preference"
            return True
        VEHICLE_NAMES = ["Sedan", "Executive SUV", "Premium SUV", "Transit VAN", "Sprinter VAN"]
        for name in VEHICLE_NAMES:
            if name.lower() in text.lower():
                slots[expected] = name
                return True
        return False
    elif expected == "phone":
        m = PHONE_RE.search(text)
        if m:
            slots[expected] = m.group()
            return True
    elif expected == "email":
        m = EMAIL_RE.search(text)
        if m:
            slots[expected] = m.group()
            return True
    elif expected in ("name", "pickup_location", "dropoff_location", "date", "time"):
        if len(text) >= 2:
            slots[expected] = _format_name(text) if expected == "name" else text
            return True
    return False


def _next_missing(slots: dict):
    for key, question in REQUIRED_SLOTS:
        if slots.get(key) is None:
            return key, question
    return None, None


def _summary(slots: dict) -> str:
    lines = ["Perfect! Here is your reservation summary:", ""]
    for key, _ in REQUIRED_SLOTS:
        if slots.get(key) or slots.get(key) == 0:
            lines.append(f"- {SLOT_LABELS[key]}: {slots[key]}")
    if slots.get("extras"):
        lines.append(f"- Extras: {', '.join(slots['extras'])}")
    if slots.get("estimated_price"):
        lines.append(f"- Estimated price: ${slots['estimated_price']}")
    lines += ["", "Would you like to confirm your reservation?"]
    return "\n".join(lines)


def _acknowledge(captured: list, slots: dict) -> str:
    if len(captured) < 2:
        return ""
    items = ", ".join(f"{SLOT_LABELS[k]}: {slots[k]}" for k in captured)
    return f"Great! I already have - {items}.\n"


def _format_history(reservations) -> str:
    if not reservations:
        return "I couldn't find any reservations for this email. Would you like to book a ride?"
    lines = [f"You have {len(reservations)} reservation(s):", ""]
    for r in reservations:
        lines.append(f"#{r.id} - {r.pickup_location} to {r.dropoff_location} on {r.pickup_date} at {r.pickup_time} - {r.status}")
    return "\n".join(lines)


def _lookup_history(email: str) -> str:
    from app.database import SessionLocal
    from app.services.reservation_service import get_user_reservations
    db = SessionLocal()
    try:
        reservations = get_user_reservations(db, email)
    finally:
        db.close()
    return _format_history(reservations)


def _compute_price(slots: dict):
    from app.database import SessionLocal
    from app.services.reservation_service import estimate_price_by_zone
    db = SessionLocal()
    try:
        price = estimate_price_by_zone(db, slots.get("pickup_location", ""), slots.get("dropoff_location", ""), slots.get("vehicle"))
        if price is not None:
            slots["estimated_price"] = price
    finally:
        db.close()


def _price_quote(pickup: str, dropoff: str, vehicle: str) -> str:
    from app.database import SessionLocal
    from app.services.reservation_service import estimate_price_by_zone

    db = SessionLocal()
    try:
        price = estimate_price_by_zone(db, pickup, dropoff, vehicle)
    finally:
        db.close()

    if price is None:
        return "Sorry, I don't have a fixed rate for this route. Please contact us for a custom quote."

    return f"A {vehicle} from {pickup} to {dropoff} would cost ${price}."


def _vehicle_info() -> str:
    from app.database import SessionLocal
    from app.models import Vehicle
    db = SessionLocal()
    try:
        vehicles = db.query(Vehicle).order_by(Vehicle.capacity).all()
    finally:
        db.close()
    lines = ["Here is our fleet:", ""]
    for v in vehicles:
        lines.append(f"- {v.name}: up to {v.capacity} passenger(s), {v.luggage} bag(s)")
    lines.append("")
    lines.append("Which one would you like to know more about, or are you ready to book?")
    return "\n".join(lines)


def _vehicle_prefix(slots: dict) -> str:
    from app.database import SessionLocal
    from app.services.reservation_service import recommend_vehicle
    db = SessionLocal()
    try:
        v = recommend_vehicle(db, slots.get("passengers") or 1, slots.get("luggage") or 0)
    finally:
        db.close()
    if v:
        slots["_recommended_vehicle"] = v.name
        return f"Based on {slots.get('passengers')} passenger(s) and {slots.get('luggage')} bag(s), I recommend the {v.name}.\n"
    return ""


def _apply_modification(session: dict, entities: dict) -> str | None:
    FIELD_MAP = [
        ("time", "pickup_time", "time"),
        ("date", "pickup_date", "date"),
        ("pickup_location", "pickup_location", None),
        ("dropoff_location", "dropoff_location", None),
        ("passengers", "passengers", None),
        ("luggage", "luggage", None),
    ]

    from app.database import SessionLocal
    from app.services.reservation_service import update_reservation, parse_date, parse_time

    for entity_key, column_name, conversion in FIELD_MAP:
        value = entities.get(entity_key)
        if value is None:
            continue

        if conversion == "time":
            value = parse_time(str(value))
        elif conversion == "date":
            value = parse_date(str(value))

        db = SessionLocal()
        try:
            ok = update_reservation(db, session["reservation_id"], column_name, value)
        finally:
            db.close()

        if ok:
            return f"Done! Your {column_name.replace('_', ' ')} has been updated to {value}."
        return "Sorry, I couldn't find that reservation."

    return None


def handle_message(conversation_id: str | None, message: str) -> dict:
    if not conversation_id or conversation_id not in SESSIONS:
        conversation_id = str(uuid.uuid4())
        SESSIONS[conversation_id] = _new_session()
    session = SESSIONS[conversation_id]

    intent = predict_intent(message)["intent"]
    entities = extract_entities(message)
    _scan_contact_info(session["slots"], message)

    if session.get("expected") == "history_email" and session["slots"].get("email"):
        session["expected"] = None
        return _reply(conversation_id, _lookup_history(session["slots"]["email"]))

    if session.get("expected") == "pricing_locations":
        _merge_entities(session["slots"], entities)
        pickup = session["slots"].get("pickup_location")
        dropoff = session["slots"].get("dropoff_location")
        if pickup and dropoff:
            session["expected"] = "pricing_vehicle"
            return _reply(conversation_id, "What type of vehicle would you like? (Sedan, Executive SUV, Premium SUV, Transit VAN, Sprinter VAN, or No Preference)")
        return _reply(conversation_id, "Could you give me both the pickup and destination?")

    if session.get("expected") == "pricing_vehicle":
        _fill_expected(session["slots"], "vehicle", message)
        vehicle = session["slots"].get("vehicle")
        if not vehicle:
            if re.search(r"\b(recommend|recommendation|suggest|your choice)\b", message, re.I):
                from app.database import SessionLocal
                from app.services.reservation_service import recommend_vehicle
                db = SessionLocal()
                try:
                    v = recommend_vehicle(db, 1, 0)
                finally:
                    db.close()
                vehicle = v.name if v else "Sedan"
                session["slots"]["vehicle"] = vehicle
            else:
                return _reply(conversation_id, "Sorry, I didn't catch the vehicle type. Please choose: Sedan, Executive SUV, Premium SUV, Transit VAN, Sprinter VAN, or No Preference.")
        session["expected"] = "pricing_compare"
        quote = _price_quote(session["slots"]["pickup_location"], session["slots"]["dropoff_location"], vehicle)
        return _reply(conversation_id, quote + "\n\n" + _vehicle_info())

    if session.get("expected") == "pricing_compare":
        VEHICLE_NAMES = ["Sedan", "Executive SUV", "Premium SUV", "Transit VAN", "Sprinter VAN"]
        found = None
        for name in VEHICLE_NAMES:
            if name.lower() in message.lower():
                found = name
                break
        if found:
            session["slots"]["vehicle"] = found
            return _reply(conversation_id, _price_quote(
                session["slots"]["pickup_location"],
                session["slots"]["dropoff_location"],
                found
            ))
        session["expected"] = None
        if intent in ("thanks", "goodbye"):
            reply = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
            return _reply(conversation_id, reply)
        return _reply(conversation_id, "Which vehicle would you like the price for? Or type 'book' to start a reservation.")

    if session.get("expected") == "edit_field":
        text = message.lower()
        matched_key = None
        for key, keywords in EDIT_FIELD_KEYWORDS.items():
            if any(re.search(r"\b" + re.escape(kw) + r"\b", text) for kw in keywords):
                matched_key = key
                break

        if not matched_key:
            return _reply(conversation_id,
                "Sorry, which field would you like to change? (pickup, destination, date, time, "
                "passengers, luggage, vehicle, name, phone, or email)")

        # On vide le slot ciblé (et le prix, s'il dépend du trajet) puis on
        # redemande sa valeur : le prochain message retombera dans le flux
        # "collecting" normal (_merge_entities / _fill_expected), qui SAIT
        # remplir un slot vide - contrairement à un slot déjà rempli.
        session["slots"][matched_key] = None
        if matched_key in ("pickup_location", "dropoff_location"):
            session["slots"]["estimated_price"] = None
        session["expected"] = matched_key
        session["stage"] = "collecting"
        return _reply(conversation_id, dict(REQUIRED_SLOTS)[matched_key])

    if session.get("expected") == "modify_detail" and session.get("reservation_id"):
        session["expected"] = None
        confirmation = _apply_modification(session, entities)
        if confirmation:
            return _reply(conversation_id, confirmation)
        return _reply(conversation_id, "I didn't catch what to change. Try: 'change my pickup time to 5pm'.")

    # =====================================================================
    # Flux principal de réservation : collecte des slots puis confirmation
    # =====================================================================
    if session["stage"] in ("collecting", "confirming"):

        if intent == "cancel_booking":
            SESSIONS[conversation_id] = _new_session()
            return _reply(conversation_id, "No problem, I've cancelled this booking process. Let me know if you need anything else!")

        if session["stage"] == "confirming":
            if intent == "confirm":
                session["stage"] = "completed"
                from app.database import SessionLocal
                from app.services.reservation_service import create_reservation
                db = SessionLocal()
                try:
                    reservation = create_reservation(db, session["slots"])
                    reservation_id = reservation.id
                finally:
                    db.close()
                session["reservation_id"] = reservation_id
                from app.models import Reservation
                from app.services.email_service import send_confirmation_email
                email_to = session["slots"].get("email")
                if email_to:
                    db2 = SessionLocal()
                    try:
                        res = db2.get(Reservation, reservation_id)
                        send_confirmation_email(email_to, res)
                    finally:
                        db2.close()
                session["slots"] = {k: v for k, v in session["slots"].items() if k in ("name", "phone", "email")}
                return _reply(conversation_id,
                    f"Your reservation has been successfully created!\n"
                    f"Reservation number: {reservation_id}\n"
                    f"A confirmation email will be sent to your address.\n"
                    f"Thank you for choosing SmartLimo!")
            if intent == "deny":
                session["stage"] = "collecting"
                session["expected"] = "edit_field"
                return _reply(conversation_id, "No problem! What would you like to change?")
            if intent in ("pricing", "payment", "vehicle_information", "help",
                          "driver_tracking", "trip_history", "tip"):
                info = INTENT_RESPONSES[intent]
                return _reply(conversation_id, info + "\n\nYour reservation is still pending - would you like to confirm it?")
            _merge_entities(session["slots"], entities)
            return _reply(conversation_id, _summary(session["slots"]))

        captured = _merge_entities(session["slots"], entities)
        if not captured:
            _fill_expected(session["slots"], session["expected"], message)

        key, question = _next_missing(session["slots"])
        if key:
            session["expected"] = key
            reco = _vehicle_prefix(session["slots"]) if key == "vehicle" else ""
            return _reply(conversation_id, _acknowledge(captured, session["slots"]) + reco + question)
        _compute_price(session["slots"])
        session["stage"] = "confirming"
        return _reply(conversation_id, _summary(session["slots"]))

    # =====================================================================
    # Hors flux de réservation : routage par intention
    # =====================================================================

    if intent == "cancel_booking":
        num_match = RESERVATION_NUM_RE.search(message)
        target_reservation_id = None

        if num_match:
            candidate_id = int(num_match.group(1))
            email = session["slots"].get("email")
            if email:
                from app.database import SessionLocal
                from app.models import Reservation, User
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.email == email).first()
                    if user:
                        res = db.query(Reservation).filter(
                            Reservation.id == candidate_id,
                            Reservation.user_id == user.id
                        ).first()
                        if res:
                            target_reservation_id = candidate_id
                finally:
                    db.close()

        reservation_id = target_reservation_id or session.get("reservation_id")

        if not reservation_id:
            return _reply(conversation_id, "Could you give me your email so I can find that reservation?")

        from app.database import SessionLocal
        from app.services.reservation_service import cancel_reservation
        db = SessionLocal()
        try:
            ok = cancel_reservation(db, reservation_id)
        finally:
            db.close()
        if ok:
            return _reply(conversation_id, f"Your reservation #{reservation_id} has been cancelled. We hope to see you again soon!")
        return _reply(conversation_id, "Sorry, I couldn't find that reservation.")

    if intent == "modify_booking":
        num_match = RESERVATION_NUM_RE.search(message)
        target_reservation_id = None

        if num_match:
            candidate_id = int(num_match.group(1))
            email = session["slots"].get("email")
            if email:
                from app.database import SessionLocal
                from app.models import Reservation, User
                db = SessionLocal()
                try:
                    user = db.query(User).filter(User.email == email).first()
                    if user:
                        res = db.query(Reservation).filter(
                            Reservation.id == candidate_id,
                            Reservation.user_id == user.id
                        ).first()
                        if res:
                            target_reservation_id = candidate_id
                finally:
                    db.close()

        reservation_id = target_reservation_id or session.get("reservation_id")

        if not reservation_id:
            return _reply(conversation_id, "I don't see an active reservation to modify. Would you like to book one, or check your past reservations?")

        session["reservation_id"] = reservation_id
        confirmation = _apply_modification(session, entities)
        if confirmation:
            return _reply(conversation_id, confirmation)
        session["expected"] = "modify_detail"
        return _reply(conversation_id, "Sure! What would you like to change? (for example: change my pickup time to 5pm)")

    if intent == "driver_tracking" and session.get("reservation_id"):
        from app.database import SessionLocal
        from app.services.reservation_service import get_reservation_route
        db = SessionLocal()
        try:
            route = get_reservation_route(db, session["reservation_id"])
        finally:
            db.close()
        if route:
            return _reply(conversation_id,
                f"Your trip is {route['distance_km']} km, about {route['duration_min']} min "
                f"from your pickup to your destination.")
        return _reply(conversation_id, "Sorry, I couldn't calculate the route for that reservation.")

    if intent == "trip_history":
        email = session["slots"].get("email")
        if email:
            return _reply(conversation_id, _lookup_history(email))
        session["expected"] = "history_email"
        return _reply(conversation_id, "Sure! May I have your email address to look up your reservations?")

    if intent == "vehicle_information":
        return _reply(conversation_id, _vehicle_info())

    if intent == "pricing":
        _merge_entities(session["slots"], entities)
        pickup = session["slots"].get("pickup_location")
        dropoff = session["slots"].get("dropoff_location")

        if not pickup or not dropoff:
            session["expected"] = "pricing_locations"
            return _reply(conversation_id, "Sure! Where would you like to travel from and to?")

        if not session["slots"].get("vehicle"):
            session["expected"] = "pricing_vehicle"
            return _reply(conversation_id, "What type of vehicle would you like? (Sedan, Executive SUV, Premium SUV, Transit VAN, Sprinter VAN, or No Preference)")

        return _reply(conversation_id, _price_quote(pickup, dropoff, session["slots"]["vehicle"]))

    if intent == "book_ride":
        session["stage"] = "collecting"
        captured = _merge_entities(session["slots"], entities)
        key, question = _next_missing(session["slots"])
        if key:
            session["expected"] = key
            prefix = _acknowledge(captured, session["slots"]) or "Great! Let's book your ride.\n"
            reco = _vehicle_prefix(session["slots"]) if key == "vehicle" else ""
            return _reply(conversation_id, prefix + reco + question)
        _compute_price(session["slots"])
        session["stage"] = "confirming"
        return _reply(conversation_id, _summary(session["slots"]))

    reply = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
    return _reply(conversation_id, reply)


def _reply(conversation_id: str, text: str) -> dict:
    return {"conversation_id": conversation_id, "reply": text}