from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.database.sync_db import SessionLocal
from app.modules.playwright.model.playwright_script_model import PlaywrightScript
from app.shared.controller import BaseController


class PlaywrightController(BaseController):

    # =========================
    # Serialização
    # =========================

    def _serialize(self, script: PlaywrightScript) -> Dict[str, Any]:
        return {
            "id": script.id,
            "analysis_id": script.analysis_id,
            "title": script.title,
            "version": script.version,
            "language": script.language,
            "status": script.status,
            "script": script.script,
            "generator_model": script.generator_model,
            "meta": script.meta,
            "error_message": script.error_message,
        }

    # =========================
    # GET
    # =========================

    async def index(self, analyses_id: int):
        db: Session = SessionLocal()
        try:
            scripts: List[PlaywrightScript] = (
                db.query(PlaywrightScript)
                .filter(PlaywrightScript.analysis_id == analyses_id)
                .order_by(PlaywrightScript.version.desc())
                .all()
            )

            return {
                "status": True,
                "message": "scripts playwright retornados com sucesso",
                "data": [self._serialize(s) for s in scripts],
            }

        except Exception as e:
            return {
                "status": False,
                "message": f"erro ao buscar scripts: {e}",
                "data": None,
            }
        finally:
            db.close()

    # =========================
    # POST (create)
    # =========================

    async def store(self, analyses_id: int, payload: Dict[str, Any]):
        db: Session = SessionLocal()
        try:
            script_code = payload.get("script")
            if not script_code:
                return {
                    "status": False,
                    "message": "script é obrigatório",
                    "data": None,
                }

            # próxima versão
            last_version = (
                db.query(func.max(PlaywrightScript.version))
                .filter(PlaywrightScript.analysis_id == analyses_id)
                .scalar()
            ) or 0

            script = PlaywrightScript(
                analysis_id=analyses_id,
                title=payload.get("title", "Playwright Script"),
                language=payload.get("language", "typescript"),
                script=script_code,
                version=last_version + 1,
                generator_model=payload.get("generator_model"),
                meta=payload.get("meta"),
                status="generated",
            )

            db.add(script)
            db.commit()
            db.refresh(script)

            return {
                "status": True,
                "message": "script playwright criado com sucesso",
                "data": self._serialize(script),
            }

        except Exception as e:
            db.rollback()
            return {
                "status": False,
                "message": f"erro ao criar script: {e}",
                "data": None,
            }
        finally:
            db.close()

    # =========================
    # PUT (update)
    # =========================

    async def update(self, analysis_id: int, version: int, payload: Dict[str, Any]):
        db: Session = SessionLocal()
        try:
            script: Optional[PlaywrightScript] = (
                db.query(PlaywrightScript)
                .filter(
                    PlaywrightScript.analysis_id == analysis_id,
                    PlaywrightScript.version == version,
                )
                .first()
            )

            if not script:
                return {
                    "status": False,
                    "message": "script não encontrado",
                    "data": None,
                }

            updatable_fields = [
                "title",
                "language",
                "status",
                "script",
                "generator_model",
                "error_message",
                "meta",
            ]

            for f in updatable_fields:
                if f in payload:
                    setattr(script, f, payload.get(f))

            db.commit()
            db.refresh(script)

            return {
                "status": True,
                "message": "script playwright atualizado com sucesso",
                "data": self._serialize(script),
            }

        except Exception as e:
            db.rollback()
            return {
                "status": False,
                "message": f"erro ao atualizar script: {e}",
                "data": None,
            }
        finally:
            db.close()
