import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from werkzeug.security import generate_password_hash
from models import User, db

EMAIL_REGEX = r"^[\w\.-]+@[\w\.-]+\.\w+$"

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# Checking whether user is admin or not
def is_admin():
    claims = get_jwt()
    return claims.get("role") == "ADMIN"


# Create user api, only admin can create
@admin_bp.route("/users", methods=["POST"])
@jwt_required()
def create_user():
    if not is_admin():
        return jsonify({"msg": "Access denied"}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"msg": "Invalid JSON body"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email")    or "").strip().lower()
    password = data.get("password")
    role = data.get("role", "USER").upper()
    is_active = data.get("is_active", True)

    if not username or not email or not password:
        return jsonify({"msg": "username, email and password are required"}), 400

    if len(password) < 8:
        return jsonify({"msg": "Password must be at least 8 characters"}), 400

    if role not in ("USER", "ADMIN"):
        return jsonify({"msg": "role must be USER or ADMIN"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"msg": "Username already exists"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"msg": "Email already exists"}), 409

    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        role=role,
        is_active=bool(is_active),
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "User created successfully", "id": user.id}), 201


#
@admin_bp.route("/users", methods=["GET"])
@jwt_required()
def get_all_users():
    if not is_admin():
        return jsonify({"msg": "Access denied"}), 403

    users = User.query.order_by(User.id).all()
    return jsonify([
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "scanned_sheets_count": u.scanned_sheets_count,
            "is_active": u.is_active,
        }
        for u in users
    ])


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
@jwt_required()
def update_user(user_id):

    if not is_admin():
        return jsonify({"msg": "Access denied"}), 403

    user = db.session.get(User, user_id)

    if not user:
        return jsonify({"msg": "User not found"}), 404

    data = request.get_json(silent=True)

    if not data:
        return jsonify({"msg": "Invalid JSON body"}), 400

    if "username" in data:

        new_username = data["username"].strip()

        if not new_username:
            return jsonify({"msg": "Username cannot be empty"}), 400

        existing_user = User.query.filter(
            User.username == new_username,
            User.id != user_id
        ).first()

        if existing_user:
            return jsonify({"msg": "Username already taken"}), 409

        user.username = new_username

    if "email" in data:

        new_email = data["email"].strip().lower()

        if not new_email:
            return jsonify({"msg": "Email cannot be empty"}), 400

        if not re.match(EMAIL_REGEX, new_email):
            return jsonify({"msg": "Invalid email format"}), 400

        existing_email = User.query.filter(
            User.email == new_email,
            User.id != user_id
        ).first()

        if existing_email:
            return jsonify({"msg": "Email already in use"}), 409

        user.email = new_email

    if "role" in data:

        new_role = data["role"].upper()

        if new_role not in ["USER", "ADMIN"]:
            return jsonify({"msg": "Role must be USER or ADMIN"}), 400

        user.role = new_role

    if "is_active" in data:

        if not isinstance(data["is_active"], bool):
            return jsonify({"msg": "is_active must be true or false"}), 400

        user.is_active = data["is_active"]

    # PASSWORD
    if "password" in data:
        new_password = data["password"]
        if len(new_password) < 8:
            return jsonify({"msg": "Password must be at least 8 characters"}), 400
        user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({"msg": "User updated successfully"}), 200


@admin_bp.route("/users/<int:user_id>", methods=["DELETE"])
@jwt_required()
def delete_user(user_id):
    if not is_admin():
        return jsonify({"msg": "Access denied"}), 403

    current_user_id = int(get_jwt_identity())
    if user_id == current_user_id:
        return jsonify({"msg": "You cannot delete your own account"}), 400

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"msg": "User not found"}), 404

    db.session.delete(user)
    db.session.commit()
    return jsonify({"msg": "User deleted successfully"})