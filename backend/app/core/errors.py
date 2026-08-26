"""Uniform JSON error responses for the whole API."""

import logging

from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException

from ..api.helpers import ApiError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def handle_api_error(exc: ApiError):
        payload: dict = {"error": exc.message}
        if exc.details:
            payload["details"] = exc.details
        return jsonify(payload), exc.status

    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        # Anything under /api answers in JSON; the SPA catch-all handles the rest.
        if request.path.startswith("/api"):
            return jsonify({"error": exc.description}), exc.code
        return exc

    @app.errorhandler(Exception)
    def handle_unexpected(exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return jsonify({"error": "Something went wrong on our side"}), 500
