from datetime import date

from pydantic import BaseModel, ConfigDict, Field


class CheckInCreate(BaseModel):
    checkin_date: date
    mood: str | None = Field(default=None, max_length=32)
    reflection: str | None = Field(default=None, max_length=5000)


class CheckInResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    checkin_date: date
    mood: str | None
    reflection: str | None
    completed_tasks: int
    total_tasks: int
