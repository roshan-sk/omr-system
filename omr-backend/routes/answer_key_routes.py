from flask import Blueprint, request, jsonify
from models import db, AnswerKey, ScoringRule
from services.answer_key_service import validate_scoring_rules
from flask_jwt_extended import jwt_required, get_jwt_identity
from models import User

answer_key_bp = Blueprint("answer_key", __name__)

DEFAULT_BASIC = [
    {
        "from": 1,
        "to": 40,
        "correct": 1,
        "wrong": 0,
        "empty": 0
    }
]

VALID_LEVELS = {
    "lower_primary",
    "upper_primary",
    "junior",
    "intermediate",
    "senior",
    "open"
}


def _is_admin():

    current_email = get_jwt_identity()

    user = User.query.filter_by(email=current_email).first()

    return user and user.role == "ADMIN"

def _sanitize_level(raw_level):
    if not raw_level or not isinstance(raw_level, str):
        return None

    sanitized = raw_level.strip().lower().replace(" ", "_")

    if not sanitized or len(sanitized) > 64:
        return None

    return sanitized


def _parse_rule_float(rule, key, default=0.0):
    try:
        return float(rule[key])
    except (KeyError, TypeError, ValueError):
        return default


def _parse_rule_int(rule, key):
    try:
        return int(rule[key])
    except (KeyError, TypeError, ValueError):
        return None



@answer_key_bp.route("/api/save_answer_key", methods=["POST"])
@jwt_required()
def save_answer_key():

    # if not _is_admin():
    #     return jsonify({"error": "Admin access required"}), 403

    data = request.get_json(silent=True)

    if not data or not isinstance(data, dict):
        return jsonify({"error": "Invalid or missing JSON body"}), 400

    raw_level = data.get("level", "")
    level = _sanitize_level(raw_level)

    if not level:
        return jsonify({"error": "Level required"}), 400

    answers = data.get("answers", {})

    if not isinstance(answers, dict):
        return jsonify({"error": "answers must be an object"}), 400

    scoring_rules = data.get("scoring_rules", [])

    if not isinstance(scoring_rules, list):
        return jsonify({"error": "scoring_rules must be a list"}), 400

    try:

        parsed_rules = []


        for index, rule in enumerate(scoring_rules):

            if not isinstance(rule, dict):
                return jsonify({"error": "Each scoring rule must be an object"}), 400

            start = _parse_rule_int(rule, "from")
            end = _parse_rule_int(rule, "to")

            if start is None or end is None:
                return jsonify({"error": "Each rule must contain valid from/to"}), 400

            parsed_rule = {
                "start_question": start,
                "end_question": end,
                "positive_marks": _parse_rule_float(rule, "correct", 1.0),
                "negative_marks": _parse_rule_float(rule, "wrong", 0.0),
                "unanswered_marks": _parse_rule_float(rule, "empty", 0.0),
            }

            parsed_rules.append(parsed_rule)


        if parsed_rules:

            validation_errors = validate_scoring_rules(parsed_rules)

            if validation_errors["invalid_ranges"]:
                return jsonify({"error": "Invalid question ranges", "details": validation_errors}), 400

            if validation_errors["overlaps"]:
                return jsonify({"error": "Overlapping ranges detected", "details": validation_errors}), 400

            if validation_errors["missing_ranges"]:
                return jsonify({"error": "Missing question coverage", "details": validation_errors}), 400


        AnswerKey.query.filter_by(level=level).delete()

        for q_str, ans in answers.items():

            try:
                q_no = int(str(q_str).replace("Q", "").strip())
            except (ValueError, AttributeError):
                continue

            if q_no < 1 or q_no > 40:
                continue

            ans_val = (
                str(ans).strip().upper()
                if ans not in [None, ""]
                else ""
            )

            existing = AnswerKey.query.filter_by(
                level=level,
                question_number=q_no
            ).first()

            if existing:
                existing.correct_answer = ans_val
            else:
                db.session.add(
                    AnswerKey(
                        level=level,
                        question_number=q_no,
                        correct_answer=ans_val
                    )
                )


        ScoringRule.query.filter_by(level=level).delete()

        for rule in parsed_rules:

            db.session.add(
                ScoringRule(
                    level=level,
                    range_from=rule["start_question"],
                    range_to=rule["end_question"],
                    correct_marks=rule["positive_marks"],
                    wrong_marks=rule["negative_marks"],
                    empty_marks=rule["unanswered_marks"]
                )
            )

        db.session.commit()

        return jsonify({"message": "Answer key and scoring rules saved successfully"}), 200

    except Exception as e:

        db.session.rollback()

        return jsonify({"error": str(e)}), 500



@answer_key_bp.route("/api/get_answer_key/<level>", methods=["GET"])
@jwt_required()
def get_answer_key(level):

    level = _sanitize_level(level)

    if not level:
        return jsonify({"error": "Invalid level"}), 400

    try:

        keys = AnswerKey.query.filter_by(level=level).all()

        answers = {
            f"Q{str(k.question_number).zfill(2)}": k.correct_answer
            for k in keys
        }

        rules_db = (
            ScoringRule.query
            .filter_by(level=level)
            .order_by(ScoringRule.range_from)
            .all()
        )


        if rules_db:

            scoring_rules = [
                {
                    "from": r.range_from,
                    "to": r.range_to,
                    "correct": r.correct_marks,
                    "wrong": r.wrong_marks,
                    "empty": r.empty_marks,
                }
                for r in rules_db
            ]

        else:
            scoring_rules = DEFAULT_BASIC

        return jsonify({"answers": answers, "scoring_rules": scoring_rules}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@answer_key_bp.route("/api/delete_scoring_rules/<level>", methods=["DELETE"])
@jwt_required()
def delete_scoring_rules(level):

    # if not _is_admin():
    #     return jsonify({
    #         "error": "Access denied. Admin permission required."
    #     }), 403

    level = _sanitize_level(level)

    if not level:
        return jsonify({"error": "Invalid level"}), 400

    try:

        deleted_count = (
            ScoringRule.query
            .filter_by(level=level)
            .delete()
        )

        db.session.commit()

        return jsonify({"message": f"Deleted {deleted_count} scoring rules for {level}"}), 200

    except Exception as e:

        db.session.rollback()

        return jsonify({"error": str(e)}), 500


@answer_key_bp.route("/api/delete_answer_keys/<level>", methods=["DELETE"])
@jwt_required()
def delete_answer_keys(level):

    # if not _is_admin():
    #     return jsonify({"error": "Admin access required"}), 403

    level = _sanitize_level(level)

    if not level:
        return jsonify({
            "error": "Invalid level"
        }), 400

    try:

        deleted_count = (
            AnswerKey.query
            .filter_by(level=level)
            .delete()
        )

        db.session.commit()

        return jsonify({
            "message": f"Deleted {deleted_count} answer keys for {level}"
        }), 200

    except Exception as e:

        db.session.rollback()

        return jsonify({
            "error": str(e)
        }), 500