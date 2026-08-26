from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class DailyTaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    emoji: str | None = Field(default=None, max_length=16)
    scheduled_for: date
    life_rule_id: int | None = None


class DailyTaskItem(BaseModel):
    """One task inside a bulk day plan."""

    title: str = Field(min_length=1, max_length=180)
    emoji: str | None = Field(default=None, max_length=16)
    life_rule_id: int | None = None
    completed: bool = False


class DailyPlanCreate(BaseModel):
    """Replace a day's plan in one call — how the Plan screen saves."""

    scheduled_for: date
    tasks: list[DailyTaskItem] = Field(default_factory=list, max_length=30)


class DailyTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    emoji: str | None
    scheduled_for: date
    life_rule_id: int | None
    completed: bool
    completed_at: datetime | None
