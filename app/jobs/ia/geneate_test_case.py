from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.geneate_test_case",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def geneate_test_case(*args, **kwargs):
    logger.info("🚀 Job GeneateTestCase iniciado", extra={
        "args": args,
        "kwargs": kwargs
    })

    # TODO: implementar lógica do job
    
    

    logger.info("✅ Job GeneateTestCase finalizado")
