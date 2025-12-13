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
