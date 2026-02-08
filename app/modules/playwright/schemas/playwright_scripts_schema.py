from typing import Optional, Dict, Any
from pydantic import BaseModel


class PlaywrightScriptCreate(BaseModel):
    analysis_id: int
    title: Optional[str] = "Playwright Script"
    language: Optional[str] = "typescript"
    script: str
    generator_model: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PlaywrightScriptUpdate(BaseModel):
    title: Optional[str] = None
    status: Optional[str] = None
    script: Optional[str] = None
    error_message: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class PlaywrightScriptResponse(BaseModel):
    id: int
    analysis_id: int
    title: str
    version: int
    language: str
    status: str
    script: str
    generator_model: Optional[str]
    meta: Optional[Dict[str, Any]]

    class Config:
        from_attributes = True
