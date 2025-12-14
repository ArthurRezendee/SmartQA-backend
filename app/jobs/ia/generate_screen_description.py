from app.core.celery_app import celery_app
import logging

logger = logging.getLogger(__name__)


@celery_app.task(
    name="jobs.ia.generate_screen_description",
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 10},
)
def generate_screen_description(*args, **kwargs):
    logger.info("🚀 Job GenerateScreenDescription iniciado", extra={
        "args": args,
        "kwargs": kwargs
    })

    # TODO: implementar lógica do job

    logger.info("✅ Job GenerateScreenDescription finalizado")
