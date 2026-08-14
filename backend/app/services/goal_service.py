from ..repositories.goal_repository import GoalRepository
from ..schemas.goal import GoalCreate

class GoalService:
    def __init__(self, repository=GoalRepository):
        self.repository = repository

    def list_goals(self, user_id: int):
        return self.repository.list_for_user(user_id)

    def create_goal(self, user_id: int, payload: GoalCreate):
        return self.repository.create(
            user_id=user_id,
            title=payload.title.strip(),
            description=payload.description.strip() if payload.description else None,
            emoji=payload.emoji,
        )
