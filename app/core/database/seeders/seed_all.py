from sqlalchemyseeder import ResolvingSeeder
from app.core.database.sync_db import SessionLocal
from app.modules.plans.model.plan_model import Plan
from app.modules.billing.model.billing_account_model import BillingAccount


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