"""
run.py — application entry point.
Run with:  python run.py
Or set FLASK_APP=run.py and use the flask CLI.
"""

from dotenv import load_dotenv
load_dotenv()  # reads .env before anything else imports os.environ

from app import app, db
from app.models import User


def seed_teacher():
    """Create 2 default accounts if none exists."""
    with app.app_context():
        db.create_all()
        if not User.query.filter_by(role="teacher").first():
            teacher = User(
                username     = "teacher",
                display_name = "Instructor",
                role         = "teacher",
                cohort       = "Staff",
            )
            student = User(
                username="hannahc",
                display_name="Student",
                role="student",
                cohort="General",
            )
            teacher.set_password("teach123")
            db.session.add(teacher)
            student.set_password("hannah123")
            db.session.add(student)
            db.session.commit()
            print("Default teacher / student account created (username: teacher / password: teach123)")


if __name__ == "__main__":
    seed_teacher()
    app.run(debug=True)