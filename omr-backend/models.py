# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class StudentOMR(db.Model):
    __tablename__ = "student_omr_results"

    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255))
    name = db.Column(db.String(100))
    level = db.Column(db.String(20))
    centre_number = db.Column(db.String(20))
    dob = db.Column(db.String(20))
    score = db.Column(db.Integer)
    answers = db.Column(db.JSON)
    verify_ans = db.Column(db.JSON)
    batch_id = db.Column(db.String(50))
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class AnswerKey(db.Model):
    __tablename__ = "answer_key"
    
    __table_args__ = (
        db.UniqueConstraint('level', 'question_number', name='unique_level_question'),
    )

    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20))
    question_number = db.Column(db.Integer)
    correct_answer = db.Column(db.String(1))
    

class ScoringRule(db.Model):
    __tablename__ = "scoring_rules"
 
    __table_args__ = (
        db.UniqueConstraint('level', 'range_from', name='unique_level_range'),
    )
 
    id = db.Column(db.Integer, primary_key=True)
    level = db.Column(db.String(20), nullable=False)
    range_from = db.Column(db.Integer, nullable=False)
    range_to = db.Column(db.Integer, nullable=False)
    correct_marks = db.Column(db.Float, nullable=False, default=1)
    wrong_marks = db.Column(db.Float, nullable=False, default=0)
    empty_marks = db.Column(db.Float, nullable=False, default=0)
    

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)

    role = db.Column(db.Enum('ADMIN', 'USER', name='user_roles'), default='USER')

    scanned_sheets_count = db.Column(db.Integer, default=0)

    is_active = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, onupdate=datetime.now)
    
    omr_results = db.relationship('StudentOMR', backref='user', lazy=True)

    def __repr__(self):
        return f"<User {self.username}>"