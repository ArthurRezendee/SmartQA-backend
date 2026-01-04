from app.core.celery_app import celery_app
import logging
from app.modules.ai.service.tests_generator_service import TestCaseAgent


logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_test_case",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def geneate_test_case(*args, **kwargs):
    logger.info(
        f"🚀 Job GenerateTestCase iniciado | kwargs={kwargs}"
    )


    # TODO: implementar lógica do job    

    logger.info("✅ Job GenerateTestCase finalizado")
