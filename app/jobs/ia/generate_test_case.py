from app.core.celery_app import celery_app
import logging

from app.modules.ai.service.tests_generator_service import TestCaseAgent
from app.modules.ai.utils.ai_utils import AiUtils
from app.core.database.sync_db import SessionLocal

from app.modules.qa_analysis.model.qa_analysis_model import QaAnalysis
from app.modules.test_case.model.test_case_model import TestCase
from app.modules.test_case.model.test_case_step_model import TestCaseStep
from app.jobs.ia._jobs import mark_job_running, mark_job_completed, mark_job_error


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
    v = str(value).strip().replace('\x00', '')
    return v if v else None


@celery_app.task(
    name="jobs.ia.generate_test_case",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def generate_test_case(*args, **kwargs):
    logger.info(f"🚀 Job GenerateTestCase iniciado | kwargs={kwargs}")

    qa_analysis_id = kwargs.get("analysis_id")
    ai_model_used = kwargs.get("ai_model_used", "gpt-4.1-mini")

    if not qa_analysis_id:
        raise ValueError("analysis_id não informado")

    db = SessionLocal()

    try:
        # ==========================================================
        # 0) busca análise e monta prompt
        # ==========================================================
        mark_job_running(db, qa_analysis_id, "test_cases")
        db.commit()

        analysis = db.query(QaAnalysis).filter(QaAnalysis.id == qa_analysis_id).first()
        if not analysis:
            raise ValueError(f"QaAnalysis {qa_analysis_id} não encontrada")

        analysis_payload = analysis.to_dict()

        if not analysis_payload.get("tests_description"):
            raise ValueError("tests_description não encontrado — descrição ainda não foi gerada")

        documents_block = None
        documents = analysis_payload.get("documents")
        if documents:
            documents_text = AiUtils.read_documents_with_docling(documents=documents)
            if documents_text and documents_text.strip():
                documents_block = AiUtils.build_documents_block(documents_text)

        test_case_prompt = AiUtils.build_test_case_prompt(
            ui_description=analysis_payload["tests_description"],
            analysis=analysis_payload,
            documents_block=documents_block,
        )

        # ==========================================================
        # 2) chama IA
        # ==========================================================
        agent = TestCaseAgent(model=ai_model_used)
        test_cases_payload = agent.generate(test_case_prompt)

        if not isinstance(test_cases_payload, list) or len(test_cases_payload) == 0:
            raise ValueError("IA retornou lista vazia de casos de teste")

        logger.info(f"[GenerateTestCase] IA retornou {len(test_cases_payload)} casos")

        # ==========================================================
        # 3) persistência
        # ==========================================================
        created_test_cases: list[TestCase] = []

        for idx, tc in enumerate(test_cases_payload, start=1):
            title = safe_text(tc.get("title"))
            if not title:
                logger.warning(f"[GenerateTestCase] Caso {idx} ignorado: sem title")
                continue

            test_case = TestCase(
                qa_analysis_id=qa_analysis_id,
                title=title[:255],
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

        db.flush()

        # ==========================================================
        # 4) steps
        # ==========================================================
        steps_to_create: list[TestCaseStep] = []

        for tc_obj, tc_payload in zip(created_test_cases, test_cases_payload):
            steps = tc_payload.get("steps") or []
            if not isinstance(steps, list) or len(steps) == 0:
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

        # ==========================================================
        # 5) marca job como concluído (verifica se batch todo terminou)
        # ==========================================================
        mark_job_completed(db, qa_analysis_id, "test_cases")
        db.commit()

        logger.info(
            f"✅ Job GenerateTestCase finalizado | "
            f"analysis_id={qa_analysis_id} | "
            f"test_cases_salvos={len(created_test_cases)} | "
            f"steps_salvos={len(steps_to_create)}"
        )

    except Exception as e:
        db.rollback()
        logger.exception(f"[GenerateTestCase] Falha: {e}")

        retries_done = getattr(generate_test_case.request, "retries", 0)
        max_retries = generate_test_case.max_retries or 0
        if retries_done >= max_retries:
            try:
                mark_job_error(db, qa_analysis_id, "test_cases", e)
                db.commit()
            except Exception:
                db.rollback()

        raise

    finally:
        db.close()