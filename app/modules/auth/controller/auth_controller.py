from app.shared.controller import BaseController
from app.modules.auth.service.auth_service import AuthService
from app.shared.responses import success, error


class AuthController(BaseController):

    def __init__(self):
        self.service = AuthService()

    async def register(self, db, data):
        try:
            user, access_token, refresh_token = await self.service.register(
                db,
                data.name,
                data.email,
                data.password
            )
            return success("Usuário criado com sucesso. Verifique seu e-mail.", {
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "email_verified": user.email_verified,
            })
        except ValueError as e:
            return error(str(e))

    async def login(self, db, data):
        try:
            user, access_token, refresh_token = await self.service.login(
                db,
                data.email,
                data.password
            )
            return success("Login realizado", {
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "email_verified": user.email_verified,
            })
        except ValueError as e:
            return error(str(e))

    async def google(self, db, data):
        try:
            user, access_token, refresh_token = await self.service.login_google(db, data.token)
            return success("Login Google realizado", {
                "user_id": user.id,
                "access_token": access_token,
                "refresh_token": refresh_token,
                "email_verified": user.email_verified,
            })
        except Exception as e:
            print("❌ Google login error:", e)
            raise

    async def refresh(self, db, data):
        try:
            access_token, refresh_token = await self.service.refresh(db, data.refresh_token)
            return success("Token renovado", {
                "access_token": access_token,
                "refresh_token": refresh_token,
            })
        except ValueError as e:
            return error(str(e))

    async def verify_email(self, db, user_id: int, data):
        try:
            await self.service.verify_email_code(db, user_id, data.code)
            return success("E-mail confirmado com sucesso")
        except ValueError as e:
            return error(str(e))

    async def forgot_password(self, db, data):
        await self.service.request_password_reset(db, data.email)
        return success("Se o e-mail estiver cadastrado, você receberá as instruções em breve.")

    async def reset_password(self, db, data):
        try:
            await self.service.reset_password(db, data.token, data.new_password)
            return success("Senha redefinida com sucesso.")
        except ValueError as e:
            return error(str(e))
