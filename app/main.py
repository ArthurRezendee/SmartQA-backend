from fastapi import FastAPI
from app.core.config import settings
from app.modules.user.router import router as user_router

app = FastAPI(
    title="SmartQA API",  
    description="SmartQA - Sistema de Qualidade de Software",  
    version="1.0.0",  
)

app.include_router(user_router)