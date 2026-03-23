import os
import resend
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).resolve().parents[3]

TEMPLATES_DIR = BASE_DIR / "templates"


class EmailService:
    def __init__(self):
        api_key = os.getenv("RESEND_API_KEY")
        if not api_key:
            raise RuntimeError("RESEND_API_KEY precisa estar definido")

        resend.api_key = api_key
        self.from_email = os.getenv("EMAIL_FROM", "SmartQA <noreply@smartqa.com.br>")

        self.env = Environment(
            loader=FileSystemLoader(TEMPLATES_DIR),
            autoescape=True,
        )

    def send_template(
        self,
        to: str,
        subject: str,
        template_name: str,
        context: dict,
    ):
        template = self.env.get_template(template_name)

        html = template.render(
            **context,
            year=datetime.now().year,
        )

        params: resend.Emails.SendParams = {
            "from": self.from_email,
            "to": [to],
            "subject": subject,
            "html": html,
        }

        resend.Emails.send(params)
