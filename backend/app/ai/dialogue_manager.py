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
    ("vehicle", "What type of vehicle would you prefer? (Sedan, Executive SUV, Premium SUV, Transit VAN, Sprinter VAN, or No Preference)"),
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
NONE_RE = re.compile(r"\b(none|no|zero|nothing)\b", re.I)

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
    text = message.strip()
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
    elif expected == "vehicle" and NO_PREF_RE.search(text):
        slots[expected] = "No Preference"
        return True
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
                return _reply(conversation_id,
                    f"Your reservation has been successfully created!\n"
                    f"Reservation number: {reservation_id}\n"
                    f"A confirmation email will be sent to your address.\n"
                    f"Thank you for choosing SmartLimo!")
            if intent == "deny":
                session["stage"] = "collecting"
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
            return _reply(conversation_id, _acknowledge(captured, session["slots"]) + question)
        session["stage"] = "confirming"
        return _reply(conversation_id, _summary(session["slots"]))

    if intent == "cancel_booking" and session.get("reservation_id"):
        from app.database import SessionLocal
        from app.services.reservation_service import cancel_reservation
        db = SessionLocal()
        try:
            ok = cancel_reservation(db, session["reservation_id"])
        finally:
            db.close()
        if ok:
            rid = session["reservation_id"]
            SESSIONS[conversation_id] = _new_session()
            return _reply(conversation_id, f"Your reservation #{rid} has been cancelled. We hope to see you again soon!")
        return _reply(conversation_id, "Sorry, I couldn't find that reservation.")

    if intent == "trip_history":
        email = session["slots"].get("email")
        if email:
            return _reply(conversation_id, _lookup_history(email))
        session["expected"] = "history_email"
        return _reply(conversation_id, "Sure! May I have your email address to look up your reservations?")

    if intent == "book_ride":
        session["stage"] = "collecting"
        captured = _merge_entities(session["slots"], entities)
        key, question = _next_missing(session["slots"])
        if key:
            session["expected"] = key
            prefix = _acknowledge(captured, session["slots"]) or "Great! Let's book your ride.\n"
            return _reply(conversation_id, prefix + question)
        session["stage"] = "confirming"
        return _reply(conversation_id, _summary(session["slots"]))

    reply = INTENT_RESPONSES.get(intent, INTENT_RESPONSES["unknown"])
    return _reply(conversation_id, reply)


def _reply(conversation_id: str, text: str) -> dict:
    return {"conversation_id": conversation_id, "reply": text}