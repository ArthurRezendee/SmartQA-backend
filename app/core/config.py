import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "SmartQA")

        self.database_url = os.getenv("DATABASE_URL")
        self.database_url_sync = os.getenv("DATABASE_URL_SYNC")

        self.SECRET_KEY = os.getenv("SECRET_KEY")
        self.JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
        self.ACCESS_TOKEN_EXPIRE_MINUTES = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

        self.GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")


settings = Settings()
