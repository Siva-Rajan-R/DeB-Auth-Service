import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pydantic import EmailStr
from dotenv import load_dotenv
import os,httpx,asyncio
from typing import Optional,List
from icecream import ic
load_dotenv()

# Email configuration
DEB_EMAIL_SERVICE_API_KEY=os.getenv("DEB_EMAIL_SERVICE_API_KEY")
DEB_EMAIL_SERVICE_API_URL=os.getenv("DEB_EMAIL_SERVICE_API_URL")

async def send_email(recivers_email:List[EmailStr],subject:str,body:str,is_html:bool) -> str | bool:
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            payload={
                "recivers_email":recivers_email,
                "subject":subject,
                "body":body,
                "is_html":is_html
            }
            headers={
                "X-Api-Key":DEB_EMAIL_SERVICE_API_KEY,
            }

            response=await client.post(
                url=DEB_EMAIL_SERVICE_API_URL,
                json=payload,
                headers=headers,
            )
            response.raise_for_status()
            
            ic("Success : Email sent successfully")
            return "Email sent successfully"
    
    except Exception as e:
        ic(f"Error : Sending Email via DebEmailService {e}")

        return False

if __name__=="__main__":
    asyncio.run(send_email(
            recivers_email=['siva967763@gmail.com'],
            subject="This is From Tibos Crm",
            body="<h1>This is a testing message from tibos crm , so dont panic ! 😂</h1>",
            is_html=True
        )
    )
