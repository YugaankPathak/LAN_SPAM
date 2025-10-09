# smtp_server.py 
import os
import time
import socket
from aiosmtpd.controller import Controller
from email import policy
from email.parser import BytesParser
from pathlib import Path
import joblib

OUT_DIR = Path("received_mails")
OUT_DIR.mkdir(parents=True, exist_ok=True)
pipeline = joblib.load("spam_filter.joblib")


def detect_host(prefer_lan=True):
    # If user provided SMTP_HOST env var, use that directly
    env = os.environ.get("SMTP_HOST")
    if env:
        return env
    if prefer_lan:
        # try to discover outgoing interface IP (works without external traffic)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # doesn't actually send packets; used only to get a usable local IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            # ignore loopback result
            if not ip.startswith("127."):
                return ip
        except Exception:
            pass
    # fallback to loopback
    return "127.0.0.1"

class SaveHandler:
    async def handle_DATA(self, server, session, envelope):
        try:
            msg = BytesParser(policy=policy.default).parsebytes(envelope.content)
            subject = msg.get("Subject", "")
            from_addr = msg.get("From", "")
            to_addr = msg.get("To", "")
            ts = time.strftime("%Y%m%dT%H%M%S")

            subj_part = "".join(c if c.isalnum() or c in "-_." else "_" for c in subject)[:50] or "no_subject"

            # Extract body text
            body = msg.get_body(preferencelist=('plain', 'html'))
            body_text = body.get_content() if body else ""

            # Combine subject + body
            text_for_prediction = subject + " " + body_text

            # FIX: pass as list
            pred = pipeline.predict([text_for_prediction])[0]

            filename = OUT_DIR / f"{ts}_{subj_part}.eml"
            with open(filename, "wb") as f:
                f.write(envelope.content)

            print(f"[{ts}] FROM={from_addr} TO={to_addr} SUBJECT={subject!r} saved->{filename}. Pred={pred}")
            return "250 Message accepted for delivery"

        except Exception as e:
            print("Error handling message:", e)
            return "451 Requested action aborted: local error in processing"

if __name__ == "__main__":
    host = detect_host()
    port = int(os.environ.get("SMTP_PORT", 1025))
    handler = SaveHandler()
    controller = Controller(handler, hostname=host, port=port)
    controller.start()
    print(f"SMTP server listening on {host}:{port} — saving mails to ./received_mails")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping SMTP server...")
        controller.stop()
