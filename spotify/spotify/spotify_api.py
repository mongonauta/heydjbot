from flask import Blueprint, render_template, redirect, request  # ,, , url_for


spotify_api = Blueprint('spotify_api', __name__)


@app.route('/callback')
def callback():
    pass


@spotify_api.route('/')
def index():
    return render_template('index.html')
