from app.core.celery_app import celery_app

@celery_app.task(name="app.jobs.user.send_welcome_email")
def send_welcome_email(user_id: int):
    print(f"📧 Enviando email de boas-vindas para o usuário {user_id}")

