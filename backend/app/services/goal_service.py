from ..models.goal import Goal
from ..repositories.goal_repository import GoalRepository
from ..schemas.goal import GoalCreate, GoalUpdate


class GoalService:
    def __init__(self, repository=GoalRepository):
        self.repository = repository

    def list_goals(self, user_id: int) -> list[Goal]:
        return self.repository.list_for_user(user_id)

    def create_goal(self, user_id: int, payload: GoalCreate) -> Goal:
        return self.repository.create(
            user_id=user_id,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            emoji=payload.emoji,
        )

    def update_goal(self, user_id: int, goal_id: int, payload: GoalUpdate) -> Goal | None:
        goal = self.repository.get_for_user(user_id, goal_id)
        if goal is None:
            return None
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(goal, field, value.strip() if isinstance(value, str) else value)
        return self.repository.save(goal)

    def delete_goal(self, user_id: int, goal_id: int) -> bool:
        goal = self.repository.get_for_user(user_id, goal_id)
        if goal is None:
            return False
        self.repository.delete(goal)
        return True
