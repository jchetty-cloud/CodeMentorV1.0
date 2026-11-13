"""
app/forms.py
WTForms form definitions for CodeMentor.

Lives inside the app package so it can import from app.models without
any circular dependency — by the time forms.py is used, models.py has
already been loaded by app/__init__.py.

The tutor interaction (code submission, follow-up chat) goes via
fetch()/JSON in app.js and is NOT handled by WTForms — only the
traditional HTML form submissions (login, register) use these classes.
"""

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import (
    DataRequired, Length, Regexp, EqualTo, ValidationError,
)


class LoginForm(FlaskForm):
    """Student and teacher sign-in."""

    username = StringField(
        "Username",
        filters=[lambda value: (value or "").strip().lower()],
        validators=[
            DataRequired(message="Please choose a username."),
            Length(min=2, max=80, message="Username must be 2–80 characters."),
            Regexp(
                r"^[a-z0-9._-]+$",
                message="Use lowercase letters, numbers, dots, hyphens and underscores only.",
            ),
        ],
        render_kw={"placeholder": "jsmith", "autocomplete": "username"},
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please enter your password."),
        ],
        render_kw={"placeholder": "••••••••", "autocomplete": "current-password"},
    )

    submit = SubmitField("Sign In →")


class RegisterForm(FlaskForm):
    """New student registration."""

    display_name = StringField(
        "Full Name",
        validators=[
            DataRequired(message="Please enter your full name."),
            Length(min=2, max=120, message="Name must be 2–120 characters."),
        ],
        render_kw={"placeholder": "Jane Smith"},
    )

    username = StringField(
        "Username",
        validators=[
            DataRequired(message="Please choose a username."),
            Length(min=2, max=80, message="Username must be 2–80 characters."),
            Regexp(
                r"^[a-z0-9._-]+$",
                message="Lowercase letters, numbers, dots, hyphens and underscores only.",
            ),
        ],
        render_kw={"placeholder": "jsmith", "autocomplete": "username"},
    )

    cohort = StringField(
        "Class / Cohort",
        validators=[
            DataRequired(message="Please enter your class or cohort name."),
            Length(min=2, max=80, message="Cohort name must be 2–80 characters."),
        ],
        render_kw={"placeholder": "e.g. CS101 Autumn 2025"},
    )

    password = PasswordField(
        "Password",
        validators=[
            DataRequired(message="Please choose a password."),
            Length(min=8, message="Password must be at least 8 characters."),
        ],
        render_kw={"placeholder": "At least 8 characters", "autocomplete": "new-password"},
    )

    confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(message="Please confirm your password."),
            EqualTo("password", message="Passwords must match."),
        ],
        render_kw={"placeholder": "Repeat your password", "autocomplete": "new-password"},
    )

    submit = SubmitField("Create Account →")

    def validate_username(self, field):
        """
        Called automatically by WTForms due to the validate_<fieldname>
        naming convention. Checks the DB for duplicate usernames.

        Importing User here (from app.models, not from app) avoids a
        circular import: app/__init__.py → models.py → (done)
                         app/__init__.py → routes.py → forms.py → models.py (already loaded, safe)
        """
        from app.models import User
        if User.query.filter_by(username=field.data.lower()).first():
            raise ValidationError(
                "That username is already taken — please choose another."
            )