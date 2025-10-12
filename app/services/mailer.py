import smtplib
from email.mime.text import MIMEText
from ..config import settings

def send_mail(subject: str, body: str):
    if not settings.MAIL_HOST:
        return
    msg = MIMEText(body, 'plain', 'utf-8')
    msg['Subject'] = subject
    msg['From'] = settings.MAIL_FROM
    msg['To'] = settings.MAIL_FROM
    with smtplib.SMTP(settings.MAIL_HOST, settings.MAIL_PORT) as s:
        s.starttls()
        if settings.MAIL_USER:
            s.login(settings.MAIL_USER, settings.MAIL_PASS)
        s.sendmail(settings.MAIL_FROM, [settings.MAIL_FROM], msg.as_string())
