import httpx
from app.core.config import settings


async def verify_google_token(id_token: str) -> dict:
    url = "https://oauth2.googleapis.com/tokeninfo"

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params={"id_token": id_token})

    if response.status_code != 200:
        raise Exception("Token Google inválido")

    data = response.json()

    if data.get("aud") != settings.GOOGLE_CLIENT_ID:
        raise Exception("Audience inválido")

    if not data.get("email_verified"):
        raise Exception("Email não verificado")

    return data
