from typing import Any, Optional
from pydantic import BaseModel


class StandardResponse(BaseModel):
    status: bool
    message: str
    data: Optional[Any] = None


def success(message: str, data: Any = None, status_code: int = 200) -> StandardResponse:
    return StandardResponse(
        status=True,
        message=message,
        data=data
    )


def error(message: str, data: Any = None, status_code: int = 400) -> StandardResponse:
    return StandardResponse(
        status=False,
        message=message,
        data=data
    )