"""
app/models.py
Database models. Imported by app/__init__.py after db is created,
so db is always available via 'from app import db'.
"""

from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone


class User(db.Model):
    id            = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(80), unique=True, nullable=False)
    display_name  = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role          = db.Column(db.String(10), default="student")  # "student" | "teacher"
    cohort        = db.Column(db.String(80), default="General")
    created_at    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    sessions      = db.relationship("TutorSession", backref="user", lazy=True)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    def __repr__(self):
        return f"<User {self.username} ({self.role})>"


class TutorSession(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    user_id      = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    action       = db.Column(db.String(30), nullable=False)
    language     = db.Column(db.String(30), default="python")
    code_snippet = db.Column(db.Text, nullable=False)
    context      = db.Column(db.Text, default="")
    response     = db.Column(db.Text, nullable=False)
    followups    = db.Column(db.Integer, default=0)
    created_at   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    followup_exchanges = db.relationship(
        "TutorFollowUp",
        backref="tutor_session",
        lazy=True,
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<TutorSession {self.id} {self.action} by user {self.user_id}>"



class TutorFollowUp(db.Model):
    """Stores each student–CodeMentor follow-up exchange."""

    id = db.Column(db.Integer, primary_key=True)

    tutor_session_id = db.Column(
        db.Integer,
        db.ForeignKey("tutor_session.id"),
        nullable=False
    )

    student_question = db.Column(db.Text, nullable=False)
    mentor_response = db.Column(db.Text, nullable=False)

    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )

    def __repr__(self):
        return f"<TutorFollowUp {self.id} for session {self.tutor_session_id}>"


