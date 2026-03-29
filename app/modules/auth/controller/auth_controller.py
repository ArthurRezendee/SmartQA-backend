from app.shared.controller import BaseController
from app.modules.auth.service.auth_service import AuthService
from app.shared.responses import success, error


class AuthController(BaseController):

    def __init__(self):
        self.service = AuthService()

    async def register(self, db, data):
        try:
            user, token = await self.service.register(
                db,
                data.name,
                data.email,
                data.password
            )
            return success("Usuário criado com sucesso. Verifique seu e-mail.", {
                "user_id": user.id,
                "token": token,
                "email_verified": user.email_verified,
            })
        except ValueError as e:
            return error(str(e))

    async def login(self, db, data):
        try:
            user, token = await self.service.login(
                db,
                data.email,
                data.password
            )
            return success("Login realizado", {
                "user_id": user.id,
                "token": token,
                "email_verified": user.email_verified,
            })
        except ValueError as e:
            return error(str(e))

    async def google(self, db, data):
        try:
            user, token = await self.service.login_google(db, data.token)
            return success("Login Google realizado", {
                "user_id": user.id,
                "token": token,
                "email_verified": user.email_verified,
            })
        except Exception as e:
            print("❌ Google login error:", e)
            raise

    async def verify_email(self, db, user_id: int, data):
        try:
            await self.service.verify_email_code(db, user_id, data.code)
            return success("E-mail confirmado com sucesso")
        except ValueError as e:
            return error(str(e))
