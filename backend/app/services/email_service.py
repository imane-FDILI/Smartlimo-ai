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
