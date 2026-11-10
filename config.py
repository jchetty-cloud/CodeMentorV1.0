import os
basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-cannot-guess-this-ever'
    DATABASE_URI = os.environ.get('DATABASE_URI') or os.environ.get('DATABASE_URL')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URI') or \
        'sqlite:///' + os.path.join(basedir, 'codementor.db')

    # Flask-WTF: how long a CSRF token stays valid (seconds)
    WTF_CSRF_TIME_LIMIT = 3600