from app.core.celery_app import celery_app
from app.modules.email.service.email_service import EmailService


@celery_app.task(name="app.jobs.organization.send_invitation_email")
def send_invitation_email(
    inviter_name: str,
    org_name: str,
    invited_email: str,
    invite_url: str,
    role: str,
):
    EmailService().send_template(
        to=invited_email,
        subject=f"Você foi convidado para {org_name} • SmartQA",
        template_name="email/organization_invitation.html",
        context={
            "title": f"Convite para {org_name}",
            "header": "Você recebeu um convite",
            "inviter_name": inviter_name,
            "org_name": org_name,
            "role": role,
            "invite_url": invite_url,
        },
    )
