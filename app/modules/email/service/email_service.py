import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

from jinja2 import Environment, FileSystemLoader


BASE_DIR = Path(__file__).resolve().parents[3]

TEMPLATES_DIR = BASE_DIR / "templates"


class EmailService:
    def __init__(self):
        self.smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("EMAIL_PORT", 587))
        self.smtp_user = os.getenv("EMAIL_USER")
        self.smtp_password = os.getenv("EMAIL_PASS")

        if not self.smtp_user or not self.smtp_password:
            raise RuntimeError("EMAIL_USER e EMAIL_PASS precisam estar definidos")

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

        msg = MIMEMultipart()
        msg["From"] = f"SmartQA <{self.smtp_user}>"
        msg["To"] = to
        msg["Subject"] = subject

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
