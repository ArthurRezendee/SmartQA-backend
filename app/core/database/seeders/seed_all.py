from sqlalchemyseeder import ResolvingSeeder
from app.core.database.sync_db import SessionLocal
# IMPORTAR MODELS AQUI
from app.modules.user.model.user_model import User
from app.modules.user.model.process_notification_model import ProcessNotification

# Screen (Tela - fonte de conhecimento)
from app.modules.screen.model.screen_model import Screen
from app.modules.screen.model.screen_document_model import ScreenDocument
from app.modules.screen.model.screen_job_model import ScreenJob

# Target (Alvo - execução de análise)
from app.modules.target.model.target_model import Target
from app.modules.target.model.target_screens_model import TargetScreen
from app.modules.screen.model.access_credential_model import AccessCredential
from app.modules.target.model.target_job_model import TargetJob

from app.modules.test_case.model.test_case_model import TestCase
from app.modules.test_case.model.test_case_step_model import TestCaseStep
from app.modules.playwright.model.playwright_script_model import PlaywrightScript
from app.modules.documentation.model.documentation_model import Documentation
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.plans.model.plan_model import Plan
from app.modules.organization.model.organization_model import Organization
from app.modules.organization.model.organization_member_model import OrganizationMember
from app.modules.organization.model.organization_invitation_model import OrganizationInvitation
from app.modules.notification.model.notification_model import Notification

def run():
    session = SessionLocal()

    try:
        seeder = ResolvingSeeder(session)

        seeder.load_entities_from_json_file(
            "app/core/database/seeders/plan_seeder.json"
        )

        session.commit()
        print("✅ Seed executado com sucesso")

    finally:
        session.close()