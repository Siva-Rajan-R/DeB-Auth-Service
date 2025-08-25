import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import EmailStr
from dotenv import load_dotenv
import os 
load_dotenv()

# Email configuration
smtp_server = "smtp.gmail.com"  # Use your SMTP server
smtp_port = 587
sender_email = os.getenv("EMAIL_USER")
sender_password = os.getenv("EMAIL_PASSWORD")

# Create a multipart message

def send_email(html_content:str, recipient_email:EmailStr,subject:str):
    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = sender_email
    message["To"] = recipient_email

    # Attach the HTML content
    mime_text = MIMEText(html_content, "html")
    message.attach(mime_text)

    # Send the email
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()  # Secure the connection
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_email, message.as_string())
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")
