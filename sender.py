# sender.py
import smtplib
import os
from email.message import EmailMessage
import time

SMTP_HOST = os.environ.get("SMTP_HOST", "192.168.31.155")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 1025))

def send_email(from_addr, to_addr, subject, body):
    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
        s.send_message(msg)
    print("Sent:", subject)

if __name__ == "__main__":
    tests = [
        ("alice@example.local", "bob@example.local", "Meeting tomorrow", "Let's meet at 10."),
        ("scammer@spammy.com", "bob@example.local", "Earn money fast", "Make $1000/day, click our link"),
        ("friend@example.local", "bob@example.local", "Project update", "The build is uploaded."),
    ]
    for frm, to, subj, body in tests:
        send_email(frm, to, subj, body)
        time.sleep(0.5)
