from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field

class DailyTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    emoji: str | None = Field(default=None, max_length=16)
    scheduled_for: date
    life_rule_id: int | None = None

class DailyTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    emoji: str | None
    scheduled_for: date
    life_rule_id: int | None
    completed: bool
    completed_at: datetime | None
