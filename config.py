import os
basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-cannot-guess-this-ever'

    DATABASE_URI = (
        os.environ.get('DATABASE_URI')
        or os.environ.get('DATABASE_URL')
    )

    local_data_dir = os.path.expanduser('~/CodeMentorData')
    os.makedirs(local_data_dir, exist_ok=True)

    SQLALCHEMY_DATABASE_URI = DATABASE_URI or (
            'sqlite:///' + os.path.join(local_data_dir, 'codementor.db')
    )

    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 300
    }

    # Flask-WTF: how long a CSRF token stays valid (seconds)
    WTF_CSRF_TIME_LIMIT = 3600
