from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


def _validate_password(value: str) -> str:
    if (
        len(value) < 12
        or not any(c.islower() for c in value)
        or not any(c.isupper() for c in value)
        or not any(c.isdigit() for c in value)
        or not any(not c.isalnum() for c in value)
    ):
        raise ValueError(
            "Password must be at least 12 characters and include upper, lower, number, and symbol"
        )
    return value


class RegisterRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=512)
    vendor_id: str = Field(min_length=2, max_length=128)
    authorized_person_name: str = Field(min_length=2, max_length=256)
    email: EmailStr
    mobile_number: str = Field(min_length=7, max_length=32)
    gstin: str | None = Field(default=None, max_length=15)
    pan: str | None = Field(default=None, max_length=10)
    udyam_number: str | None = Field(default=None, max_length=32)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)

    def validate_match(self) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class EmailTokenRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)
    confirm_password: str = Field(min_length=12, max_length=128)

    @field_validator("password")
    @classmethod
    def strong_password(cls, value: str) -> str:
        return _validate_password(value)

    def validate_match(self) -> None:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    company_name: str | None
    vendor_id: str | None
    authorized_person_name: str | None
    mobile_number: str | None
    gstin: str | None
    pan: str | None
    udyam_number: str | None
    role: str
    email_verified_at: datetime | None


class MessageOut(BaseModel):
    message: str
    verification_url: str | None = None
