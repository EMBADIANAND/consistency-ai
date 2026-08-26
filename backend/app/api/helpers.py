"""Shared request-handling helpers for the route layer."""

from datetime import date

from flask import current_app, g, jsonify, request
from pydantic import BaseModel, ValidationError

from ..services.date_utils import parse_date
from ..services.rate_limit import consume


class ApiError(Exception):
    """Raised inside a route to return a specific status without nesting try blocks."""

    def __init__(self, message: str, status: int = 400, details: object | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details


def validated(model: type[BaseModel]) -> BaseModel:
    """Parse and validate the JSON body, or raise a 400-carrying ApiError."""
    try:
        return model.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        raise ApiError(
            "Please check the highlighted fields",
            400,
            [
                {"field": ".".join(str(p) for p in err["loc"]), "message": err["msg"]}
                for err in exc.errors()
            ],
        ) from exc


def query_date(param: str = "date", fallback: date | None = None) -> date:
    try:
        return parse_date(request.args.get(param), fallback)
    except ValueError as exc:
        raise ApiError(f"{param} must use YYYY-MM-DD") from exc


def serialize(model: type[BaseModel], obj) -> dict:
    return model.model_validate(obj).model_dump(mode="json")


def serialize_many(model: type[BaseModel], objs) -> list[dict]:
    return [serialize(model, obj) for obj in objs]


def enforce_ai_quota() -> None:
    """Charge one AI request to the caller's daily allowance, or refuse.

    Call this *before* doing any model work — including before opening a
    stream, since a streamed 429 would arrive as an empty conversation bubble
    rather than an error the client can show.
    """
    settings = current_app.config.get("APP_SETTINGS")
    limit = settings.ai_daily_limit if settings else 0
    quota = consume(g.user_id, limit)
    if not quota.allowed:
        raise ApiError(
            "You've reached today's coaching limit. It resets tomorrow.",
            429,
            {"used": quota.used, "limit": quota.limit},
        )


def ok(payload, status: int = 200):
    return jsonify(payload), status
