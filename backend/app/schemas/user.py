import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Deliberately permissive: enough to catch typos and obvious junk without
# rejecting valid-but-unusual addresses.
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")


class _EmailMixin(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not EMAIL_PATTERN.match(normalized):
            raise ValueError("Enter a valid email address")
        return normalized


class RegisterPayload(_EmailMixin):
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=100)


class LoginPayload(_EmailMixin):
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: str
    display_name: str
    created_at: datetime
