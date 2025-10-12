from fastapi import APIRouter, Form, Depends
from ..db import get_db
from sqlalchemy.orm import Session
from email_validator import validate_email, EmailNotValidError
from ..services.mailer import send_mail

router = APIRouter()

@router.post("/contact")
async def contact_submit(name: str = Form(...), email: str = Form(...), phone: str = Form(''),
                         subject: str = Form(''), message: str = Form(...), db: Session = Depends(get_db)):
    try:
        validate_email(email)
    except EmailNotValidError as e:
        return {"ok": False, "error": str(e)}
    # optionally store to DB here
    try:
        send_mail(subject or "Website Contact", f"From: {name} <{email}>\nPhone: {phone}\n\n{message}")
    except Exception:
        pass
    return {"ok": True}
