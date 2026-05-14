from flask import Blueprint, request, jsonify, flash, redirect, url_for
from flask_jwt_extended import create_access_token, set_access_cookies, unset_jwt_cookies
from werkzeug.security import check_password_hash
from models import User
from models import db

auth_bp = Blueprint("auth", __name__)    


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.json

    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    user = User.query.filter_by(email=email).first()

    if not user:
        return jsonify({"msg": "No account found with this email"}), 404

    if not check_password_hash(user.password, password):
        return jsonify({"msg": "Invalid password"}), 401

    if not user.is_active:
        return jsonify({"msg": "Access denied: your account has been disabled. Please reach out to your admin."}), 403

    access_token = create_access_token(
        identity=str(user.id),
        additional_claims={
            "role": user.role
        }
    )

    response = jsonify({
        "msg": "Login successful",
        "username": user.username,
        "role": user.role
    })

    set_access_cookies(response, access_token)

    return response


@auth_bp.route("/logout", methods=["POST"])
def logout():
    response = jsonify({"msg": "Logged out"})
    unset_jwt_cookies(response)
    return response