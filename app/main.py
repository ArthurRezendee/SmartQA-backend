from fastapi import FastAPI
from dotenv import load_dotenv
from app.core.config import settings
from app.modules.qa_analysis.router import router as qa_analysis_router
from app.modules.auth.router import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from app.modules.ai.router import router as ai_router
from app.modules.test_case.router import router as test_case_router
from app.modules.playwright.router import router as playwright_router
from app.modules.documentation.router import router as documentation_router
import app.core.database.models

load_dotenv()

app = FastAPI(
    title="SmartQA API",  
    description="SmartQA - Sistema de Qualidade de Software",  
    version="1.0.0",  
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"],  
)

app.include_router(qa_analysis_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(test_case_router)
app.include_router(playwright_router)
app.include_router(documentation_router)