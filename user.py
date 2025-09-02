import sender

user="alice@example.local"
to=input("Recipient Mail: ")
subject=input("Subject: ")
message=input("Message Content: ")

sender.send_email(user, to, subject, message)