import re
import smtplib
from email.message import EmailMessage


def parse_recipients(value):
    return [address.strip() for address in re.split(r"[,;\n]", value or "") if address.strip()]


def send_report(subject, html_body, text_body, username, app_password, recipients, sender_name="FSG Fantasy Draft"):
    if not username or not app_password:
        raise ValueError("GMAIL_USERNAME and GMAIL_APP_PASSWORD are required")
    if not recipients:
        raise ValueError("At least one report recipient is required")

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = f"{sender_name} <{username}>"
    message["To"] = "undisclosed-recipients:;"
    message["Bcc"] = ", ".join(recipients)
    message.set_content(text_body)
    message.add_alternative(html_body, subtype="html")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(username, app_password)
        smtp.send_message(message)
