from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)

    spotify_user = db.Column(db.String)
    telegram_user = db.Column(db.String)

    registered_on = db.Column('registered_on', db.DateTime)

    def __init__(self, spotify_user, telegram_user):
        self.spotify_user = spotify_user
        self.telegram_user = telegram_user

        self.registered_on = datetime.utcnow()

    def get_id(self):
        return unicode(self.id)

    def __repr__(self):
        return '<User %r %r>' % (self.spotify_user, self.telegram_user)
