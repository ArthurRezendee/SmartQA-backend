from app.core.celery_app import celery_app
from app.modules.email.service.email_service import EmailService


@celery_app.task(name="app.jobs.user.send_confirmation_email")
def send_confirmation_email(user_name: str, user_email: str, code: str):
    EmailService().send_template(
        to=user_email,
        subject="Seu código de verificação • SmartQA",
        template_name="email/verification_code.html",
        context={
            "title": "Verificação de e-mail",
            "header": "Confirme seu e-mail",
            "user_name": user_name,
            "code": code,
        },
    )
