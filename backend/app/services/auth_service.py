from werkzeug.security import check_password_hash, generate_password_hash
from ..core.auth import issue_access_token
from ..core.database import db
from ..models.user import User
from ..core.config import Settings

class AuthService:
    def register(self, email: str, password: str, display_name: str) -> str:
        normalized = email.strip().lower()
        if User.query.filter_by(email=normalized).first():
            raise ValueError("An account with this email already exists")
        user = User(
            email=normalized,
            password_hash=generate_password_hash(password),
            display_name=display_name.strip(),
        )
        db.session.add(user)
        db.session.commit()
        return issue_access_token(user.id, Settings())

    def login(self, email: str, password: str) -> str:
        user = User.query.filter_by(email=email.strip().lower()).first()
        if not user or not check_password_hash(user.password_hash, password):
            raise ValueError("Invalid email or password")
        return issue_access_token(user.id, Settings())
