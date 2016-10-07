#!flask/bin/python
# -*- coding: utf-8 -*-
import json
import os
import requests

from flask import Flask, render_template, jsonify, redirect, session, request

from database import DatabaseManager

from settings.local_credentials import FLASK_KEY
from settings.local_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from settings.local_credentials import DATABASE

ACTIVITIES = ['WORK', 'RUN', 'TRAVEL', 'RELAX', 'PARTY', 'SHIT']

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


@app.route('/api/v1/song/<path:song_name>', methods=['GET'])
def song(song_name):
    url = 'https://api.spotify.com/v1/search?q={}&type=track'
    resp = requests.get(
        url=url.format(song_name)
    )

    tracks = resp.json()['tracks']['items']
    # clf = joblib.load(PICKLE)
    #

    output = []
    for track in tracks:
        track_data = {
            'track_id': track['id'],
            'track_name': track['name'],
            'track_album_id': track['album']['id'],
            'track_album_name': track['album']['name'],
            'track_popularity': track['popularity'],

            'artists': track['artists'],
            'thumb': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'external_url': track['external_urls']['spotify'],

            'activity': ACTIVITIES[1]
        }
    #
    #     track_features = get_track_features(track['id'], user['access_token'])
    #
    #     if track_features:
    #         track_features_serie = {x: track_features[x] for x in features}
    #         df = pd.DataFrame.from_records(track_features_serie, index=[0])
    #         prediction = clf.predict(df)
    #
    #         track_data['activity'] = prediction[0] if prediction and len(prediction) else None
    #
        output.append(track_data)

    return jsonify(output)


@app.route('/api/v1/save_song/<path:telegram_user>', methods=['POST'])
def save_song(telegram_user):
    manager = DatabaseManager(DATABASE)
    user_data = manager.get_user_by_telegram_id(telegram_user, access_token=True)

    track_id = request.form['track_id']
    track_features = get_track_features(track_id, user_data['access_token'])
    if not track_features:
        return ({
            'code': -1,
            'message': u'Error de autenticación. Prueba con "/conectar"'
        })

    track = {
        'track_id': track_id,
        'track_name': request.form['track_name'],
        'track_album_id': request.form['track_album_id'],
        'track_album_name': request.form['track_album_name'],
        'track_popularity': request.form['track_popularity'],
        'track_artists': request.form['artists'].split(','),

        'duration': track_features['duration_ms'] if track_features else 'NA',
        'danceability': track_features['danceability'] if track_features else 'NA',
        'energy': track_features['energy'] if track_features else 'NA',
        'key': track_features['key'] if track_features else 'NA',
        'loudness': track_features['loudness'] if track_features else 'NA',
        'mode': track_features['mode'] if track_features else 'NA',
        'speechiness': track_features['speechiness'] if track_features else 'NA',
        'acousticness': track_features['acousticness'] if track_features else 'NA',
        'instrumentalness': track_features['instrumentalness'] if track_features else 'NA',
        'liveness': track_features['liveness'] if track_features else 'NA',
        'valence': track_features['valence'] if track_features else 'NA',
        'tempo': track_features['tempo'] if track_features else 'NA'
    }

    inserted_track_id = manager.add_songs(user_data['id'], [track])
    manager.classify_song(inserted_track_id, ACTIVITIES.index(request.form['activity']))

    return jsonify({
        'code': 1,
        'message': 'Saved song succesfully!!!!'
    })


def get_track_features(track_id, access_token):
    url = 'https://api.spotify.com/v1/audio-features/{}'.format(track_id)
    resp = requests.get(
        url=url,
        headers={
            'Authorization': access_token
        }
    )
    if resp.status_code == 200:
        return resp.json()

    else:
        return None

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        debug=True
    )
