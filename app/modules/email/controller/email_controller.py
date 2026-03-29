
from app.shared.controller import BaseController
from app.modules.email.service.email_service import EmailService


class EmailController(BaseController):

    def __init__(self):
        pass

    async def index(self):
        return {
            "status": True,
            "message": "Email module ready",
            "data": None
        }

    async def test(self, to: str):
        EmailService().send_template(
            to=to,
            subject="Teste de envio • SmartQA",
            template_name="email/confirmation_email.html",
            context={
                "title": "Teste de e-mail",
                "header": "Teste de envio",
                "user_name": "Teste",
                "confirmation_url": "https://smartqa.com.br",
            },
        )
        return {
            "status": True,
            "message": f"Email enviado para {to}",
            "data": None
        }
