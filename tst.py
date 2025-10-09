import joblib

# Load saved pipeline
pipeline = joblib.load("spam_filter.joblib")

# Example test messages
new_messages = [
    "Congratulations! You’ve won a free cruise ticket, click here to claim.",
    "Hey, are we still meeting at 5 for coffee?",
    "URGENT: Your bank account has been locked. Verify at www.fakebank.com"
]

# Predict
preds = pipeline.predict(new_messages)

for msg, pred in zip(new_messages, preds):
    label = "spam" if pred == 1 else "ham"
    print(f"Message: {msg}\nPredicted: {label}\n")