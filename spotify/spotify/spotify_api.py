import json
import requests

from flask import Blueprint, render_template, redirect, request, session, jsonify

from .models import User, db
from .local_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI

spotify_api = Blueprint('spotify_api', __name__)


@spotify_api.route('/api/v1/artist/<path:artist_name>', methods=['GET'])
def artist(artist_name):
    url = 'https://api.spotify.com/v1/search?q={}&type=album'
    resp = requests.get(
        url=url.format(artist_name)
    )
    # if resp.status_code != 200:

    return jsonify(json.loads(resp.content))


@spotify_api.route('/callback', methods=['GET'])
def callback():
    code = request.args.get('code')
    url = 'https://accounts.spotify.com/api/token'

    resp = requests.post(
        url=url,
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': SPOTIFY_REDIRECT_URI,
            'client_id': SPOTIFY_CLIENT_ID,
            'client_secret': SPOTIFY_CLIENT_SECRET
        }
    )

    if resp.status_code != 200:
        print resp.json()

    else:
        token = resp.json()
        session['authorization'] = '%s %s' % (token['token_type'], token['access_token'])

    return redirect('/')


@spotify_api.route('/logout', methods=['GET'])
def logout():
    session['authorization'] = None
    session['user_info'] = None

    return redirect('/')


@spotify_api.route('/login', methods=['GET'])
def connect():
    url = 'https://accounts.spotify.com/authorize/?client_id={}&redirect_uri={}&response_type=code'
    return redirect(url.format(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_REDIRECT_URI
    ))


@spotify_api.route('/', methods=['GET'])
def index():
    if 'user_info' in session and session['user_info']:
        return render_template('index.html')

    if 'authorization' in session and session['authorization']:
        resp = requests.get(
            url='https://api.spotify.com/v1/me',
            headers={
                'Authorization': session['authorization']
            }
        )

        if resp.status_code != 200:
            session['authorization'] = None

        else:
            user_info = resp.json()
            db_user = User.query.filter(User.spotify_user == user_info['id']).first()
            if not db_user:
                db_user = User(
                    spotify_user=user_info['id'],
                    telegram_user=None
                )
                db_user.spotify_access_token = session['authorization']
                db.session.add(db_user)
                db.session.commit()

            session['user_info'] = user_info

    return render_template('index.html')
