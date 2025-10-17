# app/utils/brevo_email.py
import httpx
from pydantic import BaseModel, EmailStr
from typing import List
from dotenv import load_dotenv
import os


load_dotenv()


# Gantilah dengan API Key Brevo kamu
# BREVO_API_KEY = os.getenv("BREVO_API_KEY")
# BREVO_ENDPOINT = os.getenv("BREVO_ENDPOINT")

BREVO_API_KEY = "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"
BREVO_ENDPOINT = "https://api.brevo.com/v3/smtp/email"


async def send_brevo_email(
    sender_name: str,
    sender_email: str,
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
):
    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }

    headers = {
        "accept": "application/json",
        "api-key": BREVO_API_KEY,
        "content-type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(BREVO_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        print(response.json())
        return response.json()
