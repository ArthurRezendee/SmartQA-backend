from pydantic import BaseModel
from typing import Optional


class StressTestCreate(BaseModel):
    target_id: int
    organization_id: Optional[int] = None
