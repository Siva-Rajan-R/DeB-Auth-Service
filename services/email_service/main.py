import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import EmailStr
import asyncio
from typing import Optional, List
from icecream import ic
from configs.settings import settings

# Email configuration
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
EMAIL_USER = settings.EMAIL_USER
EMAIL_PASSWORD = settings.EMAIL_PASSWORD

def _send_email_sync(recivers_email: List[EmailStr], subject: str, body: str, is_html: bool) -> str | bool:
    try:
        if settings.MOCK_MODE:
            ic("MOCK_MODE is enabled. Overriding email recipients.", recivers_email)
            recivers_email = [settings.MOCK_EMAIL]
            subject = f"[MOCK] {subject}"

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
