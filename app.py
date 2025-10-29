import streamlit as st
import joblib
import os
from pathlib import Path
import smtplib
from email import policy
from email.parser import BytesParser
import socket

# --- Import from sender.py ---
from sender import send_email, SMTP_HOST, SMTP_PORT

# --- Setup ---
RECEIVED_MAIL_DIR = Path("received_mails")
RECEIVED_MAIL_DIR.mkdir(exist_ok=True)

# List of simulated LAN users
LAN_USERS = {
    "Alice": "alice@example.local",
    "Bob": "bob@example.local",
    "Charlie": "charlie@lan.local",
    "Sarthak": "sarthak@lan.local",
    "Yugaank": "yugaank@lan.local",
    "Naziya": "naziya@lan.local",
    "Tanishq": "tanishq@lan.local"
}

# --- Load Spam Filter Model ---
try:
    if not Path("spam_filter.joblib").exists():
        st.error("Error: 'spam_filter.joblib' not found. Please ensure it's in the same directory.")
    pipeline = joblib.load("spam_filter.joblib")
    st.session_state.spam_filter_loaded = True
except Exception as e:
    st.warning(f"Could not load spam filter model: {e}")
    st.session_state.spam_filter_loaded = False
    pipeline = None


# --- Helper Functions ---

def detect_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_received_mails(recipient_email):
    if not st.session_state.spam_filter_loaded:
        return []

    mails_data = []
    eml_files = sorted(RECEIVED_MAIL_DIR.glob("*.eml"), key=os.path.getmtime, reverse=True)

    for file_path in eml_files:
        try:
            with open(file_path, 'rb') as fp:
                msg = BytesParser(policy=policy.default).parse(fp)

            subject = msg.get("Subject", "No Subject")
            to_addr = msg.get("To", "").lower().strip()

            if recipient_email.lower() not in to_addr:
                continue

            body = msg.get_body(preferencelist=('plain', 'html'))
            body_text = body.get_content() if body else ""
            text_for_prediction = subject + " " + body_text

            prediction = pipeline.predict([text_for_prediction])[0]
            label = "SPAM" if prediction == 1 else "HAM (Not Spam)"

            mails_data.append({
                "Timestamp": file_path.name.split('_')[0],
                "From": msg.get("From", "Unknown"),
                "Subject": subject,
                "Spam Status": label,
                "Body Snippet": body_text[:80] + "..." if len(body_text) > 80 else body_text,
                "File": file_path.name
            })
        except Exception as e:
            st.error(f"Could not process file {file_path.name}: {e}")

    return mails_data


# --- Detect Current User from Environment ---
USER_NAME = os.getenv("USER_NAME", "Unknown User")

matched_email = None
for name, email in LAN_USERS.items():
    if USER_NAME.lower() in name.lower() or USER_NAME.lower() in email.lower():
        matched_email = email
        selected_user_name = name
        break

if not matched_email:
    selected_user_name = USER_NAME
    matched_email = f"{USER_NAME.lower()}@lan.local"

selected_email = matched_email

st.set_page_config(page_title=f"{selected_user_name}'s Mail Client")

# --- Sidebar Info ---
st.sidebar.header("Current User")
st.sidebar.info(f"**Identity:** {selected_user_name}\n\n**Email:** `{selected_email}`")
st.sidebar.markdown("---")

st.sidebar.header("Network Info")
st.sidebar.info(f"**SMTP Server IP:** `{SMTP_HOST}:{SMTP_PORT}`\n\n**Your Client IP:** `{detect_local_ip()}`")
st.sidebar.markdown("---")


# =========================================================================
# 1. MAIL SENDER
# =========================================================================
st.title("✉️ LAN Spam Filter")
st.markdown("---")
st.header("1. Mail Sender")
st.subheader(f"Sending as: `{selected_email}`")

with st.form("sender_form"):
    from_address = st.text_input("From Address", value=selected_email, disabled=True)

    recipient_options = [email for name, email in LAN_USERS.items() if email != selected_email]
    to_address = st.selectbox("Recipient Mail:", recipient_options, key="sender_to")

    subject = st.text_input("Subject", key="sender_subject")
    message_content = st.text_area("Message Content", height=150, key="sender_body")

    submitted = st.form_submit_button("Send Email")

    if submitted:
        if not (to_address and subject and message_content):
            st.warning("Please fill in all fields.")
            st.stop()

        try:
            send_email(from_address, to_address, subject, message_content)
            st.success(f"📧 Email Sent! Subject: '{subject}' to {to_address}.")
            st.info("The message is now waiting in the server's directory. Check the recipient's view.")
        except ConnectionRefusedError:
            st.error(f"❌ Connection Error: Could not connect to {SMTP_HOST}:{SMTP_PORT}.")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

st.markdown("---")


# =========================================================================
# 2. RECEIVER INBOX
# =========================================================================
st.header("2. Inbox for Current User")
st.subheader(f"Viewing Inbox for: `{selected_email}`")

if st.session_state.spam_filter_loaded:
    if st.button("Refresh Inbox & Rerun Spam Check"):
        st.rerun()

    mails_data = get_received_mails(selected_email)

    if not mails_data:
        st.info(f"No emails found for {selected_user_name} in the received_mails directory yet.")
    else:
        st.subheader(f"Inbox Status ({len(mails_data)} Emails Found)")

        for mail in mails_data:
            subject_line = f"From: {mail['From']} | Subject: {mail['Subject']}"

            if mail['Spam Status'] == "SPAM":
                with st.expander(f"🚨 SPAM - {subject_line}", expanded=True):
                    st.error("This email was classified as SPAM and moved to Junk.")
                    st.write(f"**Body Preview:** {mail['Body Snippet']}")
            else:
                with st.expander(f"✅ HAM - {subject_line}", expanded=False):
                    st.success("This email was classified as HAM (Not Spam).")
                    st.write(f"**Body Preview:** {mail['Body Snippet']}")
else:
    st.error("The spam filter model could not be loaded. Prediction unavailable.")

st.markdown("---")


# =========================================================================
# 3. STANDALONE SPAM TESTER
# =========================================================================
st.header("3. Standalone Spam Tester")
st.caption("Quickly test any subject/body combination against the model.")

if st.session_state.spam_filter_loaded:
    with st.form("spam_test_form"):
        test_subject = st.text_input("Test Subject", key="test_subject")
        test_body = st.text_area("Test Body", key="test_body", height=100)

        test_submitted = st.form_submit_button("Predict Spam/Ham")

        if test_submitted:
            text_for_prediction = test_subject + " " + test_body
            if text_for_prediction.strip():
                try:
                    prediction = pipeline.predict([text_for_prediction])[0]
                    label = "SPAM" if prediction == 1 else "HAM (Not Spam)"

                    if label == "SPAM":
                        st.warning(f"⚠️ Prediction: {label}")
                    else:
                        st.info(f"✨ Prediction: {label}")
                except Exception as e:
                    st.error(f"Error during prediction: {e}")
            else:
                st.warning("Please enter some content to test.")
