#!flask/bin/python
# -*- coding: utf-8 -*-
import os
import requests

from flask import Flask, render_template, jsonify, redirect, session, request

from database import DatabaseManager

from settings.local_credentials import FLASK_KEY
from settings.local_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from settings.local_credentials import DATABASE

app = Flask(__name__)

app.secret_key = FLASK_KEY
app.static_folder = os.path.join(os.getcwd(), 'static/')


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/api/v1/connect/<path:telegram_user>/<path:telegram_first_name>/', methods=['GET'])
def connect(telegram_user, telegram_first_name):
    session['telegram_user'] = telegram_user
    session['telegram_first_name'] = telegram_first_name

    url = 'https://accounts.spotify.com/authorize/?client_id={}&redirect_uri={}&response_type=code&scope=playlist-modify-private'
    return redirect(url.format(
        SPOTIFY_CLIENT_ID,
        SPOTIFY_REDIRECT_URI
    ))


@app.route('/callback', methods=['GET'])
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
        access_token = '%s %s' % (token['token_type'], token['access_token'])
        refresh_token = token['refresh_token']

        resp = requests.get(
            url='https://api.spotify.com/v1/me',
            headers={
                'Authorization': access_token
            }
        )

        if resp.status_code == 200:
            user_data = resp.json()

            manager = DatabaseManager(DATABASE)
            manager.create_user(
                session['telegram_user'],
                session['telegram_first_name'],
                user_data['id'],
                access_token,
                refresh_token
            )

    return redirect('/')


@app.route('/api/v1/user_info/<path:telegram_user>/', methods=['GET'])
def user_info(telegram_user):
    manager = DatabaseManager(DATABASE)
    user = manager.get_user_by_telegram_id(telegram_user)

    return jsonify(user)


@app.route('/api/v1/stats/<path:telegram_user>/', methods=['GET'])
def stats(telegram_user):
    manager = DatabaseManager(DATABASE)
    return jsonify(manager.stats(telegram_user))


@app.route('/api/v1/train/<path:telegram_user>/', methods=['GET'])
def train(telegram_user):
    manager = DatabaseManager(DATABASE)
    unclassified_song = manager.get_unclassified_songs(telegram_user)

    if not unclassified_song:
        return jsonify({
            'code': 0,
            'message': 'All your song are trained.'
        })

    else:
        return jsonify({
            'code': 1,
            'song': unclassified_song
        })


@app.route('/api/v1/classify/<path:song_id>/<path:activity>', methods=['GET'])
def classify(song_id, activity):
    manager = DatabaseManager(DATABASE)

    return jsonify({
        'code': 1,
        'updated': manager.classify_song(song_id, activity)
    })


@app.route('/api/v1/create_playlist/<path:telegram_user>/<path:activity_id>/')
def create_playlist(telegram_user, activity_id):
    playlist_name = 'Hey DJ bot Amazing playlist'

    manager = DatabaseManager(DATABASE)

    user_data = manager.get_user_by_telegram_id(telegram_user, access_token=True)
    classified_songs = manager.get_activity_songs(telegram_user, activity_id, 10)

    resp = requests.get(
        url='https://api.spotify.com/v1/users/{}/playlists'.format(user_data['spotify_id']),
        headers={
            'Authorization': user_data['access_token']
        }
    )
    if resp.status_code != 200:
        return jsonify({
            'code': -1,
            'message': u'Error de autenticación. Prueba con "/conectar"'
        })

    else:
        playlist_id = None
        for playlist in resp.json()['items']:
            if playlist['name'] == playlist_name:
                playlist_id = playlist['id']
                break

        if not playlist_id:
            resp = requests.post(
                url='https://api.spotify.com/v1/users/{}/playlists'.format(user_data['spotify_id']),
                headers={
                    'Authorization': user_data['access_token']
                },
                data='{\"name\": \"Hey DJ bot Amazing playlist\", \"public\": false}'
            )
            if resp.status_code != 201:
                return jsonify({
                    'code': -1,
                    'message': u'Error de autenticación. Prueba con "/conectar"'
                })

            else:
                playlist_id = resp.json()['id']

        resp = requests.put(
            url='https://api.spotify.com/v1/users/{}/playlists/{}/tracks'.format(
                user_data['spotify_id'],
                playlist_id
            ),
            headers={
                'Authorization': user_data['access_token']
            },
            data='{\"uris\": [ %s ]}' % ','.join(['\"spotify:track:%s\"' % x['spotify_id'] for x in classified_songs])
        )

        if resp.status_code != 201:
            return jsonify({
                'code': -1,
                'message': u'Error de autenticación. Prueba con "/conectar"'
            })

        else:
            return jsonify({
                'code': 1,
                'message': u'Lista creada correctamente'
            })

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        debug=True
    )
