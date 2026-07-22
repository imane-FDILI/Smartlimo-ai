import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv
load_dotenv()

SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

def send_confirmation_email(to_email: str, reservation) -> bool:
    """Envoie l'email de confirmation d'une reservation (en anglais, donnees reelles)."""
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

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = to_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False
    