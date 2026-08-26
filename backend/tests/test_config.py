import pytest

from app.core.config import Settings, _normalize_database_url


@pytest.mark.parametrize(
    ("given", "expected"),
    [
        # Render and Heroku hand out this scheme; SQLAlchemy 2.x rejects it.
        ("postgres://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),
        ("postgresql://u:p@host:5432/db", "postgresql+psycopg2://u:p@host:5432/db"),
        ("mysql://u:p@host:3306/db", "mysql+pymysql://u:p@host:3306/db"),
        ("mysql+pymysql://u:p@host:3306/db", "mysql+pymysql://u:p@host:3306/db"),
        ("sqlite:///consistency_ai.db", "sqlite:///consistency_ai.db"),
    ],
)
def test_database_urls_are_normalized(given, expected):
    assert _normalize_database_url(given) == expected


def test_production_refuses_placeholder_secrets():
    unsafe = Settings(env="production", secret_key="development-only-change-me")
    problems = unsafe.validate()
    assert any("SECRET_KEY" in problem for problem in problems)


def test_production_with_real_secrets_has_no_complaints():
    safe = Settings(env="production", secret_key="a-real-secret", jwt_secret_key="another")
    assert safe.validate() == []


def test_development_does_not_complain():
    assert Settings(env="development").validate() == []
