from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: EmailStr
    fullName: str = Field(min_length=2, max_length=150)
    password: str = Field(min_length=8, max_length=72)

    @field_validator("username", "email", "fullName")
    @classmethod
    def strip_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be blank")
        return value


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=72)


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=1)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    email: str
    fullName: str
    isActive: bool


class AuthResponse(BaseModel):
    user: UserResponse
    accessToken: str
    refreshToken: str
