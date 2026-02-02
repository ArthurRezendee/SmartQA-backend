from app.core.celery_app import celery_app
import logging
from sqlalchemy.exc import SQLAlchemyError

from app.modules.ai.service.tests_generator_service import TestCaseAgent
from app.core.database.sync_db import SessionLocal

from app.modules.test_case.model.test_case_model import TestCase 
from app.modules.test_case.model.test_case_step_model import TestCaseStep 


logger = logging.getLogger(__name__)


ALLOWED_TEST_TYPE = {"functional", "regression", "smoke", "exploratory"}
ALLOWED_SCENARIO_TYPE = {"positive", "negative", "edge"}
ALLOWED_PRIORITY = {"low", "medium", "high", "critical"}
ALLOWED_RISK = {"low", "medium", "high"}


def normalize_enum(value: str, allowed: set, default: str) -> str:
    if not value:
        return default
    v = str(value).strip().lower()
    return v if v in allowed else default


def safe_text(value):
    if value is None:
        return None
    v = str(value).strip()
    return v if v else None


@celery_app.task(
    name="jobs.ia.generate_test_case",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def generate_test_case(*args, **kwargs):
    """
    kwargs esperado:
      - qa_analysis_id: int
      - test_case_prompt: str
      - ai_model_used: str (opcional)
    """
    logger.info(f"🚀 Job GenerateTestCase iniciado | kwargs={kwargs}")

    qa_analysis_id = kwargs.get("qa_analysis_id")
    test_case_prompt = kwargs.get("test_case_prompt")
    ai_model_used = kwargs.get("ai_model_used", "gpt-4.1-mini")

    if not qa_analysis_id:
        raise ValueError("qa_analysis_id não informado")
    if not test_case_prompt:
        raise ValueError("test_case_prompt não informado")

    db = SessionLocal()

    try:
        # 1) chama IA
        agent = TestCaseAgent(model=ai_model_used)
        test_cases_payload = agent.generate(test_case_prompt)  # List[dict]

        if not isinstance(test_cases_payload, list) or len(test_cases_payload) == 0:
            raise ValueError("IA retornou lista vazia de casos de teste")

        logger.info(f"[GenerateTestCase] IA retornou {len(test_cases_payload)} casos")

        # 2) persistência em transação
        created_test_cases: list[TestCase] = []

        for idx, tc in enumerate(test_cases_payload, start=1):
            title = safe_text(tc.get("title"))
            if not title:
                logger.warning(f"[GenerateTestCase] Caso {idx} ignorado: sem title")
                continue

            test_case = TestCase(
                qa_analysis_id=qa_analysis_id,
                title=title[:255],  # garante limite
                description=safe_text(tc.get("description")),
                objective=safe_text(tc.get("objective")),

                test_type=normalize_enum(tc.get("test_type"), ALLOWED_TEST_TYPE, "functional"),
                scenario_type=normalize_enum(tc.get("scenario_type"), ALLOWED_SCENARIO_TYPE, "positive"),
                priority=normalize_enum(tc.get("priority"), ALLOWED_PRIORITY, "medium"),
                risk_level=normalize_enum(tc.get("risk_level"), ALLOWED_RISK, "medium"),

                preconditions=safe_text(tc.get("preconditions")),
                expected_result=safe_text(tc.get("expected_result")),

                status="generated",

                generated_by_ai=True,
                ai_model_used=ai_model_used,
            )

            db.add(test_case)
            created_test_cases.append(test_case)

        # flush para obter IDs
        db.flush()

        # 3) steps
        steps_to_create: list[TestCaseStep] = []

        for tc_obj, tc_payload in zip(created_test_cases, test_cases_payload):
            steps = tc_payload.get("steps") or []
            if not isinstance(steps, list) or len(steps) == 0:
                # sem steps, ainda pode salvar o caso
                continue

            for st in steps:
                order = st.get("order")
                action = safe_text(st.get("action"))
                expected = safe_text(st.get("expected_result"))

                if order is None or not action or not expected:
                    continue

                steps_to_create.append(
                    TestCaseStep(
                        test_case_id=tc_obj.id,
                        order=int(order),
                        action=action,
                        expected_result=expected,
                        step_type="action",
                    )
                )

        if steps_to_create:
            db.bulk_save_objects(steps_to_create)

        db.commit()

        logger.info(
            f"✅ Job GenerateTestCase finalizado | "
            f"analysis_id={qa_analysis_id} | "
            f"test_cases_salvos={len(created_test_cases)} | "
            f"steps_salvos={len(steps_to_create)}"
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.exception(f"[GenerateTestCase] Erro SQLAlchemy: {e}")
        raise

    except Exception as e:
        db.rollback()
        logger.exception(f"[GenerateTestCase] Falha geral: {e}")
        raise

    finally:
        db.close()
