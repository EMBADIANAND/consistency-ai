from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        """A message of pure whitespace passes ``min_length`` but says nothing.

        Without this it is stored as an empty user turn, which then reaches the
        model as a blank message and leaves a blank bubble in the thread.
        """
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("message cannot be empty")
        return cleaned


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str | None
    created_at: datetime
