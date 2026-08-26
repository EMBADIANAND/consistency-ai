from ..core.database import db
from ..models.goal import Goal


class GoalRepository:
    @staticmethod
    def list_for_user(user_id: int) -> list[Goal]:
        return (
            Goal.query.filter_by(user_id=user_id, is_active=True)
            .order_by(Goal.created_at.desc())
            .all()
        )

    @staticmethod
    def get_for_user(user_id: int, goal_id: int) -> Goal | None:
        return Goal.query.filter_by(id=goal_id, user_id=user_id).first()

    @staticmethod
    def create(user_id: int, title: str, description: str | None, emoji: str | None) -> Goal:
        goal = Goal(user_id=user_id, title=title, description=description, emoji=emoji)
        db.session.add(goal)
        db.session.commit()
        return goal

    @staticmethod
    def save(goal: Goal) -> Goal:
        db.session.commit()
        return goal

    @staticmethod
    def delete(goal: Goal) -> None:
        db.session.delete(goal)
        db.session.commit()
