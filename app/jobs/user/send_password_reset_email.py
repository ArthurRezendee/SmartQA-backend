from app.core.celery_app import celery_app
from app.modules.email.service.email_service import EmailService


@celery_app.task(name="app.jobs.user.send_password_reset_email")
def send_password_reset_email(user_name: str, user_email: str, reset_url: str):
    EmailService().send_template(
        to=user_email,
        subject="Redefinição de senha • SmartQA",
        template_name="email/password_reset.html",
        context={
            "title": "Redefinição de senha",
            "header": "Redefinir senha",
            "user_name": user_name,
            "reset_url": reset_url,
        },
    )
