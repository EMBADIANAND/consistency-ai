from flask import Blueprint, g, jsonify, request
from pydantic import ValidationError
from ...core.auth import require_auth
from ...core.database import db
from ...models.life_rule import LifeRule
from ...schemas.life_rule import LifeRuleCreate, LifeRuleResponse

life_rules_bp = Blueprint("life_rules", __name__)

@life_rules_bp.get("/life-rules")
@require_auth
def list_rules():
    rules = LifeRule.query.filter_by(user_id=g.user_id, is_active=True).order_by(LifeRule.created_at.desc()).all()
    return jsonify([LifeRuleResponse.model_validate(r).model_dump(mode="json") for r in rules])

@life_rules_bp.post("/life-rules")
@require_auth
def create_rule():
    try:
        payload = LifeRuleCreate.model_validate(request.get_json(silent=True) or {})
    except ValidationError as exc:
        return jsonify({"error": "Invalid life rule", "details": exc.errors()}), 400
    rule = LifeRule(user_id=g.user_id, **payload.model_dump())
    db.session.add(rule)
    db.session.commit()
    return jsonify(LifeRuleResponse.model_validate(rule).model_dump(mode="json")), 201
