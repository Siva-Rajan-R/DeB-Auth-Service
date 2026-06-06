import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import EmailStr
from dotenv import load_dotenv
import os, asyncio
from typing import Optional, List
from icecream import ic

load_dotenv()

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

def _send_email_sync(recivers_email: List[EmailStr], subject: str, body: str, is_html: bool) -> str | bool:
    try:
        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = ", ".join(recivers_email)
        msg['Subject'] = subject

        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            
        ic("Success : Email sent successfully")
        return "Email sent successfully"
    
    except Exception as e:
        ic(f"Error : Sending Email via SMTP {e}")
        return False

async def send_email(recivers_email: List[EmailStr], subject: str, body: str, is_html: bool) -> str | bool:
    return await asyncio.to_thread(_send_email_sync, recivers_email, subject, body, is_html)

if __name__ == "__main__":
    asyncio.run(send_email(
            recivers_email=['siva967763@gmail.com'],
            subject="This is From Tibos Crm",
            body="<h1>This is a testing message using internal SMTP, so dont panic ! 😂</h1>",
            is_html=True
        )
    )
