import os

from flask import Flask
from jinja2 import FileSystemLoader, ChoiceLoader, PackageLoader

from .spotify_api import spotify_api
from .models import db
from .local_credentials import FLASK_KEY


class AngularFlask(Flask):
    jinja_options = Flask.jinja_options.copy()
    jinja_options.update(dict(
        block_start_string='<%',
        block_end_string='%>',
        variable_start_string='%%',
        variable_end_string='%%',
        comment_start_string='<#',
        comment_end_string='#>',
    ))

app = AngularFlask(__name__)
app.secret_key = FLASK_KEY

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///../spotify.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True

app.jinja_loader = ChoiceLoader([
    FileSystemLoader(os.path.join(os.getcwd(), 'templates')),
    PackageLoader('spotify'),
])

db.init_app(app)
app.register_blueprint(spotify_api)
app.static_folder = os.path.join(os.getcwd(), 'static/dist/')

__version__ = '1.0.0'
