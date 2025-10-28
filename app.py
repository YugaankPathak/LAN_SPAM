import streamlit as st
import joblib
import os
from pathlib import Path
import smtplib
from email import policy
from email.parser import BytesParser
import socket

# --- DIRECTLY IMPORTING FROM YOUR sender.py ---
from sender import send_email, SMTP_HOST, SMTP_PORT 

# --- Constants and Setup ---
RECEIVED_MAIL_DIR = Path("received_mails")
RECEIVED_MAIL_DIR.mkdir(exist_ok=True) # Ensure directory exists

# List of simulated LAN users
LAN_USERS = {
    "Alice (Sender)": "alice@example.local",
    "Bob (Receiver)": "bob@example.local",
    "Charlie (Tester)": "charlie@lan.local",
    "Sarthak": "sarthak@lan.local",
    "Yugaank": "yugaank@lan.local",
    "Naziya": "naziya@lan.local",
    "Tanishq": "tanishq@lan.local"
}

# Load the spam filter model for the prediction section
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
    """Tries to find the non-loopback IP address for display."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_received_mails(recipient_email):
    """Reads all .eml files, extracts subject/body, predicts spam status, and filters by recipient."""
    if not st.session_state.spam_filter_loaded:
        return []

    mails_data = []
    
    # 1. Get all .eml files
    eml_files = sorted(RECEIVED_MAIL_DIR.glob("*.eml"), key=os.path.getmtime, reverse=True)
    
    for file_path in eml_files:
        try:
            # 2. Parse the email file
            with open(file_path, 'rb') as fp:
                msg = BytesParser(policy=policy.default).parse(fp)
                
            subject = msg.get("Subject", "No Subject")
            # Extract recipient from the 'To' header
            to_addr = msg.get("To", "").lower().strip()
            
            # --- LAN USER FILTERING ---
            # Check if this mail is intended for the currently selected user
            if recipient_email.lower() not in to_addr:
                continue # Skip mail not addressed to this user
            
            # Extract body text (prefer plain text)
            body = msg.get_body(preferencelist=('plain', 'html'))
            body_text = body.get_content() if body else ""
            
            # 3. Predict Spam Status
            text_for_prediction = subject + " " + body_text
            
            # Prediction (1=SPAM, 0=HAM)
            prediction = pipeline.predict([text_for_prediction])[0]
            label = "SPAM" if prediction == 1 else "HAM (Not Spam)"
            
            # 4. Store data
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

# --- Streamlit App Layout ---

st.title("✉️ LAN Spam Filter")
st.markdown("---")

# --- USER SELECTION (Simulating different users on the LAN) ---
st.sidebar.header("Current User")
selected_user_name = st.sidebar.selectbox("Select Your Identity:", list(LAN_USERS.keys()))
selected_email = LAN_USERS[selected_user_name]
st.sidebar.markdown(f"**Email:** `{selected_email}`")
st.sidebar.markdown("---")

# --- NETWORK INFO ---
st.sidebar.header("Network Info")
st.sidebar.info(f"**SMTP Server IP:** `{SMTP_HOST}:{SMTP_PORT}`\n\n**Your Client IP:** `{detect_local_ip()}`")
st.sidebar.markdown("---")


# =========================================================================
# 1. SENDER SIDE: ONLY SENDS THE MESSAGE 
# =========================================================================
st.header("1. Mail Sender")
st.subheader(f"Sending as: `{selected_email}`")

with st.form("sender_form"):
    from_address = st.text_input("From Address", value=selected_email, disabled=True)
    
    # Allow sending to any user
    recipient_options = [email for name, email in LAN_USERS.items() if email != selected_email]
    to_address = st.selectbox("Recipient Mail:", recipient_options, key="sender_to")
    
    subject = st.text_input("Subject", key="sender_subject")
    message_content = st.text_area("Message Content", height=150, key="sender_body")

    submitted = st.form_submit_button("Send Email")

    if submitted:
        if not (to_address and subject and message_content):
            st.warning("Please fill in all fields.")
            st.stop()
            
        # --- Attempt to Send Email ---
        try:
            send_email(from_address, to_address, subject, message_content)
            st.success(f"📧 **Email Sent!** Subject: '{subject}' to {to_address}.")
            st.info("The message is now waiting in the server's directory. Check the Receiver Interface on the recipient's view.")
        except ConnectionRefusedError:
            st.error(f"❌ Connection Error: Could not connect to the SMTP server at {SMTP_HOST}:{SMTP_PORT}.")
            st.info("Please ensure your `smtp_server.py` script is running in a separate terminal and accessible on the network.")
        except Exception as e:
            if "connection unexpectedly closed" in str(e).lower() or "server didn't respond" in str(e).lower():
                 st.error(f"❌ SMTP Error: The server at {SMTP_HOST}:{SMTP_PORT} is not responding or closed the connection.")
                 st.info("Verify `smtp_server.py` is running and accessible.")
            else:
                st.error(f"An unexpected error occurred: {e}")
            

st.markdown("---")

# =========================================================================
# 2. RECEIVER SIDE: SHOWS RECEIVED MAILS AND PREDICTS SPAM
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
        
        # Display each mail
        for mail in mails_data:
            subject_line = f"From: {mail['From']} | Subject: {mail['Subject']}"
            
            if mail['Spam Status'] == "SPAM":
                # Use st.expander for a collapsible view, with a red background/icon for alert
                with st.expander(f"🚨 SPAM - {subject_line}", expanded=True):
                    st.error("This email was classified as **SPAM** and moved to Junk.")
                    st.write(f"**Body Preview:** {mail['Body Snippet']}")
            else:
                # Green icon for HAM
                with st.expander(f"✅ HAM - {subject_line}", expanded=False):
                    st.success("This email was classified as **HAM** and delivered to the Inbox.")
                    st.write(f"**Body Preview:** {mail['Body Snippet']}")
else:
    st.error("The Spam Filter prediction feature is unavailable because the model could not be loaded.")

st.markdown("---")

# =========================================================================
# 3. STANDALONE SPAM TESTER: For quick testing of phrases 
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
