from app import app
from models import db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    existing = User.query.filter_by(email="admin@gmail.com").first()

    if existing:
        print("Admin already exists")
    else:
        admin = User(
            username="admin",
            email="admin@gmail.com",
            password=generate_password_hash("Admin@1234"),
            role="ADMIN",
            is_active=True
        )

        db.session.add(admin)
        db.session.commit()

        print("Admin created successfully")