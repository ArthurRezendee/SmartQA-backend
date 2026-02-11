from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session, joinedload

from app.core.database.sync_db import SessionLocal
from app.modules.test_case.model.test_case_model import TestCase
from app.modules.test_case.model.test_case_step_model import TestCaseStep
from app.shared.controller import BaseController
import datetime


class TestCaseController(BaseController):
    def __init__(self):
        pass

    # =========================
    # Helpers
    # =========================

    def _serialize_step(self, step: TestCaseStep) -> Dict[str, Any]:
        return {
            "id": step.id,
            "test_case_id": step.test_case_id,
            "order": step.order,
            "action": step.action,
            "expected_result": step.expected_result,
            "step_type": step.step_type,
            "deleted_at": step.deleted_at
        }

    def _serialize_test_case(self, tc: TestCase) -> Dict[str, Any]:
        return {
            "id": tc.id,
            "qa_analysis_id": tc.qa_analysis_id,
            "title": tc.title,
            "description": tc.description,
            "objective": tc.objective,
            "test_type": tc.test_type,
            "scenario_type": tc.scenario_type,
            "priority": tc.priority,
            "risk_level": tc.risk_level,
            "preconditions": tc.preconditions,
            "postconditions": tc.postconditions,
            "expected_result": tc.expected_result,
            "status": tc.status,
            "has_automation": tc.has_automation,
            "automation_status": tc.automation_status,
            "generated_by_ai": tc.generated_by_ai,
            "ai_model_used": tc.ai_model_used,
            "ai_confidence_score": tc.ai_confidence_score,
            "steps": [self._serialize_step(s) for s in (tc.steps or [])],
            "deleted_at": tc.deleted_at
        }

    def _validate_steps_payload(self, steps: Any):
        if steps is None:
            return

        if not isinstance(steps, list):
            raise ValueError("steps deve ser uma lista")

        for i, s in enumerate(steps):
            if not isinstance(s, dict):
                raise ValueError(f"steps[{i}] deve ser um objeto")

            if "action" not in s or not s["action"]:
                raise ValueError(f"steps[{i}].action é obrigatório")

            if "expected_result" not in s or not s["expected_result"]:
                raise ValueError(f"steps[{i}].expected_result é obrigatório")

            if "order" in s and s["order"] is not None:
                if not isinstance(s["order"], int):
                    raise ValueError(f"steps[{i}].order deve ser inteiro")

    # =========================
    # GET
    # =========================

    async def index(self, analyses_id: int):
        db: Session = SessionLocal()
        try:
            test_cases: List[TestCase] = (
                db.query(TestCase)
                .options(joinedload(TestCase.steps))
                .filter(TestCase.qa_analysis_id == analyses_id)
                .order_by(TestCase.id.asc())
                .all()
            )

            return {
                "status": True,
                "message": "casos de teste retornados com sucesso",
                "data": [self._serialize_test_case(tc) for tc in test_cases],
            }
        finally:
            db.close()

    # =========================
    # POST (create)
    # =========================

    async def store(self, analyses_id: int, payload: Dict[str, Any]):
        """
        payload exemplo:
        {
          "title": "...",
          "description": "...",
          "objective": "...",
          "test_type": "functional",
          "scenario_type": "positive",
          "priority": "medium",
          "risk_level": "medium",
          "preconditions": "...",
          "postconditions": "...",
          "expected_result": "...",
          "status": "generated",
          "has_automation": false,
          "automation_status": "not_generated",
          "generated_by_ai": true,
          "ai_model_used": "gpt-4.1-mini",
          "ai_confidence_score": 0.82,
          "steps": [
            {"order": 1, "action": "...", "expected_result": "...", "step_type": "action"},
            {"order": 2, "action": "...", "expected_result": "...", "step_type": "assertion"}
          ]
        }
        """
        db: Session = SessionLocal()
        try:
            title = (payload or {}).get("title")
            if not title:
                return {
                    "status": False,
                    "message": "title é obrigatório",
                    "data": None,
                }

            steps_payload = (payload or {}).get("steps", [])
            self._validate_steps_payload(steps_payload)

            tc = TestCase(
                qa_analysis_id=analyses_id,
                title=title,
                description=payload.get("description"),
                objective=payload.get("objective"),
                test_type=payload.get("test_type", "functional"),
                scenario_type=payload.get("scenario_type", "positive"),
                priority=payload.get("priority", "medium"),
                risk_level=payload.get("risk_level", "medium"),
                preconditions=payload.get("preconditions"),
                postconditions=payload.get("postconditions"),
                expected_result=payload.get("expected_result"),
                status=payload.get("status", "generated"),
                has_automation=payload.get("has_automation", False),
                automation_status=payload.get("automation_status", "not_generated"),
                generated_by_ai=payload.get("generated_by_ai", True),
                ai_model_used=payload.get("ai_model_used"),
                ai_confidence_score=payload.get("ai_confidence_score"),
            )

            db.add(tc)
            db.flush()  # garante tc.id

            # cria steps
            if steps_payload:
                for idx, s in enumerate(steps_payload):
                    step = TestCaseStep(
                        test_case_id=tc.id,
                        order=s.get("order", idx + 1),
                        action=s["action"],
                        expected_result=s["expected_result"],
                        step_type=s.get("step_type", "action"),
                    )
                    db.add(step)

            db.commit()

            # reload com steps
            tc = (
                db.query(TestCase)
                .options(joinedload(TestCase.steps))
                .filter(TestCase.id == tc.id)
                .first()
            )

            return {
                "status": True,
                "message": "caso de teste criado com sucesso",
                "data": self._serialize_test_case(tc),
            }

        except ValueError as e:
            db.rollback()
            return {"status": False, "message": str(e), "data": None}
        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao criar caso de teste: {e}", "data": None}
        finally:
            db.close()

    # =========================
    # PUT (update + sync steps)
    # =========================

    async def update(self, analyses_id: int, test_case_id: int, payload: Dict[str, Any]):
        """
        Atualiza o test case e sincroniza steps:
        - step com id => update
        - step sem id => create
        - step existente que não veio => delete
        """
        db: Session = SessionLocal()
        try:
            tc: Optional[TestCase] = (
                db.query(TestCase)
                .options(joinedload(TestCase.steps))
                .filter(TestCase.id == test_case_id)
                .filter(TestCase.qa_analysis_id == analyses_id)
                .first()
            )

            if not tc:
                return {
                    "status": False,
                    "message": "caso de teste não encontrado",
                    "data": None,
                }

            # atualiza campos simples (só se veio no payload)
            updatable_fields = [
                "title",
                "description",
                "objective",
                "test_type",
                "scenario_type",
                "priority",
                "risk_level",
                "preconditions",
                "postconditions",
                "expected_result",
                "status",
                "has_automation",
                "automation_status",
                "generated_by_ai",
                "ai_model_used",
                "ai_confidence_score",
            ]

            for f in updatable_fields:
                if f in payload:
                    setattr(tc, f, payload.get(f))

            # steps sync
            if "steps" in payload:
                steps_payload = payload.get("steps")
                self._validate_steps_payload(steps_payload)

                existing_by_id: Dict[int, TestCaseStep] = {s.id: s for s in (tc.steps or [])}
                received_ids: set[int] = set()

                # atualiza/cria
                for idx, s in enumerate(steps_payload or []):
                    step_id = s.get("id")

                    if step_id is not None:
                        received_ids.add(step_id)

                        if step_id not in existing_by_id:
                            return {
                                "status": False,
                                "message": f"step id={step_id} não pertence a esse caso de teste",
                                "data": None,
                            }

                        step_obj = existing_by_id[step_id]
                        if "order" in s:
                            step_obj.order = s.get("order", step_obj.order)
                        step_obj.action = s["action"]
                        step_obj.expected_result = s["expected_result"]
                        step_obj.step_type = s.get("step_type", step_obj.step_type)

                    else:
                        new_step = TestCaseStep(
                            test_case_id=tc.id,
                            order=s.get("order", idx + 1),
                            action=s["action"],
                            expected_result=s["expected_result"],
                            step_type=s.get("step_type", "action"),
                        )
                        db.add(new_step)

                # delete steps que não vieram
                for step in list(tc.steps or []):
                    if step.id not in received_ids and step.id is not None:
                        db.delete(step)

            db.commit()

            tc = (
                db.query(TestCase)
                .options(joinedload(TestCase.steps))
                .filter(TestCase.id == tc.id)
                .first()
            )

            return {
                "status": True,
                "message": "caso de teste atualizado com sucesso",
                "data": self._serialize_test_case(tc),
            }

        except ValueError as e:
            db.rollback()
            return {"status": False, "message": str(e), "data": None}
        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao atualizar caso de teste: {e}", "data": None}
        finally:
            db.close()

    async def soft_delete(self, analyses_id: int, test_case_id: int):
        db: Session = SessionLocal()
        try:
            tc = (
                db.query(TestCase)
                .filter(TestCase.id == test_case_id)
                .filter(TestCase.qa_analysis_id == analyses_id)
                .first()
            )

            if not tc:
                return {"status": False, "message": "caso de teste não encontrado", "data": None}

            tc.deleted_at = datetime.datetime.utcnow()
            db.commit()

            return {"status": True, "message": "caso de teste apagado com sucesso", "data": self._serialize_test_case(tc)}

        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao apagar caso de teste: {e}", "data": None}
        finally:
            db.close()


    async def restore(self, analyses_id: int, test_case_id: int, restore_status: str = "generated"):
        db: Session = SessionLocal()
        try:
            tc = (
                db.query(TestCase)
                .filter(TestCase.id == test_case_id)
                .filter(TestCase.qa_analysis_id == analyses_id)
                .first()
            )

            if not tc:
                return {"status": False, "message": "caso de teste não encontrado", "data": None}

            if not tc.deleted_at:
                return {"status": False, "message": "caso de teste não está apagado", "data": None}

            tc.deleted_at = None
            db.commit()

            return {"status": True, "message": "caso de teste recuperado com sucesso", "data": self._serialize_test_case(tc)}

        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao recuperar caso de teste: {e}", "data": None}
        finally:
            db.close()


    async def step_soft_delete(self, analyses_id: int, test_case_id: int, step_id: int):
        db: Session = SessionLocal()
        try:
            step = (
                db.query(TestCaseStep)
                .join(TestCase, TestCase.id == TestCaseStep.test_case_id)
                .filter(TestCase.qa_analysis_id == analyses_id)
                .filter(TestCase.id == test_case_id)
                .filter(TestCaseStep.id == step_id)
                .first()
            )

            if not step:
                return {"status": False, "message": "step não encontrado", "data": None}

            step.deleted_at = datetime.datetime.utcnow()
            db.commit()

            return {"status": True, "message": "step apagado com sucesso", "data": {"id": step.id}}

        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao apagar step: {e}", "data": None}
        finally:
            db.close()


    async def step_restore(self, analyses_id: int, test_case_id: int, step_id: int):
        db: Session = SessionLocal()
        try:
            step = (
                db.query(TestCaseStep)
                .join(TestCase, TestCase.id == TestCaseStep.test_case_id)
                .filter(TestCase.qa_analysis_id == analyses_id)
                .filter(TestCase.id == test_case_id)
                .filter(TestCaseStep.id == step_id)
                .first()
            )

            if not step:
                return {"status": False, "message": "step não encontrado", "data": None}

            step.deleted_at = None
            db.commit()

            return {"status": True, "message": "step recuperado com sucesso", "data": {"id": step.id}}

        except Exception as e:
            db.rollback()
            return {"status": False, "message": f"erro ao recuperar step: {e}", "data": None}
        finally:
            db.close()