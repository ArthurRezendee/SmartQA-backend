from enum import Enum
from pydantic import BaseModel

class AnalysisRequirement(str, Enum):
    TEST_CASES = "test_cases"
    SCRIPTS = "scripts"
    DOCUMENTATION = "documentation"

class AnalyzeRequest(BaseModel):
    requirements: list[AnalysisRequirement] = []