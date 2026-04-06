from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from app.core.config import settings
from app.modules.screen.router import router as screen_router
from app.modules.target.router import router as target_router
from app.modules.auth.router import router as auth_router
from fastapi.middleware.cors import CORSMiddleware
from app.modules.ai.router import router as ai_router
from app.modules.test_case.router import router as test_case_router
from app.modules.playwright.router import router as playwright_router
from app.modules.documentation.router import router as documentation_router
from app.modules.user.router import router as user_router
from app.modules.organization.router import router as organization_router
from app.modules.plans.router import router as plans_router
from app.modules.email.router import router as email_router
from app.modules.notification.router import router as notification_router
import app.core.database.models

load_dotenv()

app = FastAPI(
    title="SmartQA API",
    description="SmartQA - Sistema de Qualidade de Software",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(screen_router)
app.include_router(target_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(test_case_router)
app.include_router(playwright_router)
app.include_router(documentation_router)
app.include_router(user_router)
app.include_router(organization_router)
app.include_router(plans_router)
app.include_router(email_router)
app.include_router(notification_router)

app.mount("/dados", StaticFiles(directory="/dados"), name="dados")
