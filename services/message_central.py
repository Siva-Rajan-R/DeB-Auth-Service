import base64
import httpx
import os
from dotenv import load_dotenv

load_dotenv()

MESSAGE_CENTRAL_CUSTOMER_ID = os.getenv("MESSAGE_CENTRAL_CUSTOMER_ID", "")
MESSAGE_CENTRAL_PASSWORD = os.getenv("MESSAGE_CENTRAL_PASSWORD", "")

def parse_phone(phone: str):
    """
    Parses a phone number string and returns a tuple (country_code, mobile_number).
    Defaults country_code to "91" if not parsed.
    """
    clean_phone = "".join(c for c in phone if c.isdigit() or c == '+')
    if clean_phone.startswith('+'):
        num_only = clean_phone.replace('+', '')
        if len(num_only) > 10:
            country_code = num_only[:-10]
            mobile_number = num_only[-10:]
            return country_code, mobile_number
        else:
            return "91", num_only
    else:
        if len(clean_phone) == 10:
            return "91", clean_phone
        elif len(clean_phone) > 10:
            return clean_phone[:-10], clean_phone[-10:]
        return "91", clean_phone

class MessageCentral:
    BASE_URL = "https://cpaas.messagecentral.com"

    def __init__(self):
        self.customer_id = MESSAGE_CENTRAL_CUSTOMER_ID
        self.password = MESSAGE_CENTRAL_PASSWORD

    async def _get_token(self) -> str:
        if not self.customer_id or not self.password:
            raise ValueError("Message Central Customer ID and Password are not configured in environment variables.")
        
        encoded_password = base64.b64encode(
            self.password.encode()
        ).decode()

        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.BASE_URL}/auth/v1/authentication/token",
                params={
                    "customerId": self.customer_id,
                    "key": encoded_password,
                    "scope": "NEW",
                    "country": "91",
                },
            )
        response.raise_for_status()
        data = response.json()
        return data["token"]

    async def send_otp(self, phone: str, otp_length: int = 6):
        country_code, mobile_number = parse_phone(phone)
        token = await self._get_token()
        
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{self.BASE_URL}/verification/v3/send",
                params={
                    "customerId": self.customer_id,
                    "countryCode": country_code,
                    "mobileNumber": mobile_number,
                    "flowType": "SMS",
                    "otpLength": otp_length,
                },
                headers={
                    "authToken": token
                },
            )
        response.raise_for_status()
        return response.json()

    async def verify_otp(self, verification_id: str, otp: str):
        token = await self._get_token()
        
        headers = {
            "authToken": token,
        }
        params = {
            "verificationId": verification_id,
            "code": otp,
        }
        
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.BASE_URL}/verification/v3/validateOtp",
                params=params,
                headers=headers,
            )
        response.raise_for_status()
        return response.json()
