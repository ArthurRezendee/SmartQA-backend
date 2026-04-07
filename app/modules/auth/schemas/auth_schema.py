from pydantic import BaseModel, EmailStr


class RegisterSchema(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginSchema(BaseModel):
    email: EmailStr
    password: str


class GoogleAuthSchema(BaseModel):
    token: str  # token JWT do Google


class VerifyEmailSchema(BaseModel):
    code: str


class ForgotPasswordSchema(BaseModel):
    email: EmailStr


class ResetPasswordSchema(BaseModel):
    token: str
    new_password: str


class RefreshTokenSchema(BaseModel):
    refresh_token: str
