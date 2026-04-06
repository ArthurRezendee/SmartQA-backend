import logging
import os
import hashlib

import app.core.database.models
from app.core.celery_app import celery_app
from app.core.database.sync_db import SessionLocal
from app.modules.screen.service.screen_service import ScreenService
from app.modules.screen.model.screen_model import Screen
from app.modules.screen.model.access_credential_model import AccessCredential
from app.modules.ai.utils.ai_utils import AiUtils
from app.modules.ai.service.docs_generator_service import DocumentationAgent
from app.modules.ai.service.screen_explorer_service import ScreenExplorerService
from app.modules.documentation.model.documentation_model import Documentation
from sqlalchemy import func


logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_documentation",
    autoretry_for=(),
)
def generate_documentation(*, screen_id: int, user_id: int):
    logger.info(
        "🚀 Job generate_documentation iniciado",
        extra={"screen_id": screen_id, "user_id": user_id},
    )

    db = SessionLocal()

    try:
        screen_service = ScreenService()
        screen = screen_service.get_or_fail_sync(
            db=db,
            screen_id=screen_id,
            user_id=user_id,
        )

        if not isinstance(screen, dict):
            screen = screen.to_dict()

        # Carrega credenciais com valores para o BrowserUse
        credentials = (
            db.query(AccessCredential)
            .filter(AccessCredential.screen_id == screen_id)
            .all()
        )
        credentials_list = [
            {"field_name": c.field_name, "value": c.value} for c in credentials
        ]

        # Executa análise via BrowserUse para gerar documentation_description
        screen_url = screen.get("url")
        if screen_url:
            logger.info(
                "🌐 Iniciando análise BrowserUse para geração de documentação",
                extra={"screen_id": screen_id},
            )
            explorer_service = ScreenExplorerService()
            explorer_payload = {
                "id": screen_id,
                "name": screen.get("name"),
                "target_url": screen_url,
                "description": screen.get("description", ""),
                "screen_context": screen.get("screen_context", ""),
                "access_credentials": credentials_list,
            }

            descriptions = explorer_service.generate_screen_descriptions(
                analysis=explorer_payload
            )

            db.query(Screen).filter(Screen.id == screen_id).update(
                {
                    "documentation_description": descriptions["documentation_description"],
                    "uiux_description": descriptions["uiux_description"],
                },
                synchronize_session=False,
            )
            db.commit()

            documentation_description = descriptions["documentation_description"]
            logger.info(
                "✅ BrowserUse concluído — documentation_description salva",
                extra={"screen_id": screen_id},
            )
        else:
            documentation_description = screen.get("documentation_description", "")
            logger.info(
                "⚠️ Tela sem URL — usando documentation_description existente",
                extra={"screen_id": screen_id},
            )

        analysis_payload = {
            "id": screen_id,
            "name": screen.get("name"),
            "target_url": screen_url or "N/A",
            "description": screen.get("description", ""),
            "screen_context": screen.get("screen_context", ""),
            "documentation_description": documentation_description,
        }

        docs_prompt = AiUtils.build_docs_prompt(analysis=analysis_payload)

        logger.info(
            "🧠 Prompt Docs gerado",
            extra={"screen_id": screen_id},
        )

        ai_model_used = os.getenv("OPENAI_MODEL_DOCS", "gpt-4.1-mini")

        agent = DocumentationAgent(model=ai_model_used)
        documentation_text = agent.generate(docs_prompt)

        last_version = (
            db.query(func.max(Documentation.version))
            .filter(Documentation.screen_id == screen_id)
            .scalar()
        ) or 0

        next_version = last_version + 1

        title = screen.get("name") or f"Documentação funcional - Tela {screen_id}"

        prompt_hash = hashlib.sha256(docs_prompt.encode()).hexdigest()

        documentation = Documentation(
            screen_id=screen_id,
            title=title,
            version=next_version,
            status="generated",
            content=documentation_text,
            content_format="text",
            generated_by="ai",
            generator_model=ai_model_used,
            prompt_hash=prompt_hash,
        )

        db.add(documentation)
        db.commit()

        logger.info(
            "✅ Documentação gerada e salva com sucesso",
            extra={"screen_id": screen_id, "version": next_version},
        )

        return {
            "screen_id": screen_id,
            "documentation_version": next_version,
            "status": "completed",
        }

    except Exception as e:
        db.rollback()
        logger.exception("❌ Erro no job generate_documentation")
        raise

    finally:
        db.close()
