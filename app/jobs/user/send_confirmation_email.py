from app.core.celery_app import celery_app
from app.modules.email.service.email_service import EmailService

@celery_app.task(name="app.jobs.user.send_confirmation_email")
def send_confirmation_email(user_id: int):
    # 🔥 Aqui você buscaria no banco
    user = {
        "id": user_id,
        "email": "arezendealmeida@gmail.com",
        "name": "Arthur"
    }

    token = "token-confirmacao"
    confirmation_url = f"https://smartqa.io/confirm-email?token={token}"

    email_service = EmailService()

    email_service.send_template(
        to=user["email"],
        subject="Confirme seu e-mail • SmartQA",
        template_name="email/confirmation_email.html",
        context={
            "title": "Confirmação de e-mail",
            "header": "Confirme seu e-mail",
            "user_name": user["name"],
            "confirmation_url": confirmation_url,
        },
    )

    print(f"📧 Email de confirmação enviado para {user['email']}")
