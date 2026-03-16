from sqlalchemyseeder import ResolvingSeeder
from app.core.database.sync_db import SessionLocal
from app.modules.plans.model.plan_model import Plan
from app.modules.billing.model.billing_account_model import BillingAccount
from app.modules.organization.model.organization_model import Organization
from app.modules.user.model.user_model import User
from app.modules.organization.model.organization_member_model import OrganizationMember
from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.qa_analysis.model.qa_document_model import QaDocument
from app.modules.qa_analysis.model.access_credential_model import AccessCredential
from app.modules.test_case.model.test_case_model import TestCase
from app.modules.test_case.model.test_case_step_model import TestCaseStep
from app.modules.user.model.process_notification_model import ProcessNotification
from app.modules.playwright.model.playwright_script_model import PlaywrightScript
from app.modules.documentation.model.documentation_model import Documentation


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