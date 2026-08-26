from pydantic import BaseModel, ConfigDict, Field


class GoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    emoji: str | None = Field(default=None, max_length=16)


class GoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    emoji: str | None = Field(default=None, max_length=16)
    is_active: bool | None = None


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str | None
    emoji: str | None
    is_active: bool
