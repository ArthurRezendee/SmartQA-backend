import os
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.core.security import create_email_confirmation_token
from app.modules.email.service.email_service import EmailService
from app.modules.user.model.user_model import User


@celery_app.task(name="app.jobs.user.send_confirmation_email")
def send_confirmation_email(user_id: int):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return
    finally:
        db.close()

    token = create_email_confirmation_token(user.id)
    frontend_url = os.getenv("FRONTEND_URL", "https://smartqa.com.br")
    confirmation_url = f"{frontend_url}/confirm-email?token={token}"

    EmailService().send_template(
        to=user.email,
        subject="Confirme seu e-mail • SmartQA",
        template_name="email/confirmation_email.html",
        context={
            "title": "Confirmação de e-mail",
            "header": "Confirme seu e-mail",
            "user_name": user.name,
            "confirmation_url": confirmation_url,
        },
    )
