import os
import smtplib
from email.message import EmailMessage

SMTP_HOST = os.getenv("SMTP_HOST", "host.docker.internal")
SMTP_PORT = int(os.getenv("SMTP_PORT", "1025"))

def send_mail(to, subject, body):
    msg = EmailMessage()
    msg["From"] = "external@outside.com"
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.send_message(msg)
        print(f"Sent mail to {to}")

if __name__ == "__main__":
    send_mail("alice@example.local", "Hello Alice", "Hi Alice, hope you're doing well.")
    send_mail("bob@example.local", "Spam Offer", "You won $10,000! Click to claim now!")
