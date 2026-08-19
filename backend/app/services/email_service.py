"""
SmartLimo AI - Service d'envoi d'emails

Envoie l'email de confirmation de réservation via un serveur SMTP réel
(Gmail), en utilisant des identifiants stockés dans les variables
d'environnement (jamais en dur dans le code, pour éviter de committer des
secrets). Appelé depuis dialogue_manager.handle_message juste après la
création d'une réservation en base.
"""

import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

# Identifiants du compte SMTP utilisé pour l'envoi (lus depuis le fichier
# .env). SMTP_PASSWORD doit être un "mot de passe d'application" Gmail
# (et non le mot de passe du compte) si l'authentification à deux facteurs
# est activée.
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_confirmation_email(to_email: str, reservation) -> bool:
    """Envoie l'email de confirmation d'une reservation (en anglais, donnees reelles).

    `reservation` est un objet ORM Reservation (voir models.py) : ses
    attributs (pickup_location, pickup_date, vehicle, price...) sont lus
    directement pour composer le corps de l'email.
    Retourne True si l'envoi a réussi, False sinon (l'appelant n'interrompt
    pas le flux de réservation en cas d'échec, l'email n'est qu'une
    notification annexe).
    """
    # Le véhicule peut ne pas encore être assigné à cette étape ("No
    # Preference" côté utilisateur) : on affiche un texte de repli.
    vehicle_name = reservation.vehicle.name if reservation.vehicle else "To be assigned"
    price_line = f"- Estimated price: ${reservation.price}\n" if reservation.price else ""

    subject = f"SmartLimo - Reservation #{reservation.id} confirmed"
    body = f"""Hello,

Your limousine reservation is confirmed!

Reservation details:
- Reservation number: {reservation.id}
- Pickup: {reservation.pickup_location}
- Destination: {reservation.dropoff_location}
- Date: {reservation.pickup_date}
- Time: {reservation.pickup_time}
- Vehicle: {reservation.vehicle.name if reservation.vehicle else "To be assigned"}
{price_line}
Thank you for choosing SmartLimo!

The SmartLimo Team
"""

    # MIMEText encapsule le corps du message avec les en-têtes email
    # nécessaires (Subject/From/To) pour former un message valide.
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        # SMTP_SSL établit une connexion chiffrée directe (port 465) avec
        # le serveur SMTP de Gmail, contrairement à STARTTLS qui négocie
        # le chiffrement après une connexion en clair.
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        # On n'interrompt jamais la réservation à cause d'un échec d'email :
        # on logue simplement l'erreur et on renvoie False.
        print(f"Email error: {e}")
        return False

def send_admin_notification_email(reservation, user) -> bool:
    """Envoie une notification a l'equipe (Bee Digital) des qu'une nouvelle
    reservation est creee, pour verification manuelle avant l'envoi
    eventuel d'un devis personnalise au client.
    `reservation` est l'objet ORM Reservation, `user` l'objet ORM User
    associe (pour recuperer nom/email/telephone du client)."""
    admin_email = os.getenv("ADMIN_NOTIFICATION_EMAIL", SMTP_USER)
    subject = f"New SmartLimo reservation #{reservation.id} - Review needed"
    body = f"""A new reservation has just been submitted through SmartLimo AI.

Client information:
- Name: {user.name}
- Email: {user.email}
- Phone: {user.phone}

Reservation details:
- Reservation number: {reservation.id}
- Pickup: {reservation.pickup_location}
- Destination: {reservation.dropoff_location}
- Date: {reservation.pickup_date}
- Time: {reservation.pickup_time}
- Passengers: {reservation.passengers}
- Luggage: {reservation.luggage}
- Vehicle: {reservation.vehicle.name if reservation.vehicle else "Not specified"}
- Estimated price: ${reservation.price if reservation.price else "N/A"}
- Child seat requested: {"Yes" if reservation.child_seat_requested else "No"}

Please review and confirm availability before sending a personalized quote to the client.
"""
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = admin_email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, admin_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Failed to send admin notification email: {e}")
        return False