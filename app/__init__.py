from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
import anthropic

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
csrf = CSRFProtect(app)   # protects all HTML form POSTs automatically

import os

api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY is missing from the environment.")

client = anthropic.Anthropic(api_key=api_key)

from app import routes, models

with app.app_context():
    db.create_all()
