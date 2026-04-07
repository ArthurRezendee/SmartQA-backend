from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys

# -------------------------------------------------
# PYTHONPATH
# -------------------------------------------------
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(BASE_DIR)

from app.core.config import settings
from app.core.base import Base

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


config = context.config

config.set_main_option(
    "sqlalchemy.url",
    settings.database_url_sync
)

target_metadata = Base.metadata


def run_migrations_offline():
    context.configure(
        url=settings.database_url_sync,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
