from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import anthropic

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)   # protects all HTML form POSTs automatically

client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

from app import routes, models

with app.app_context():
    db.create_all()
