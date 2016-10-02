#!flask/bin/python
import json
import os
import requests

from flask import Flask, render_template, jsonify, redirect, session, request

import pandas as pd

from sklearn import svm
from sklearn.externals import joblib

from database import DatabaseManager

from settings.local_credentials import FLASK_KEY
from settings.local_credentials import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
from settings.local_credentials import DATABASE, PICKLE

app = Flask(__name__)

app.secret_key = FLASK_KEY
app.static_folder = os.path.join(os.getcwd(), 'static/')

features = [
    'danceability', 'energy', 'loudness', 'speechiness', 'acousticness',
    'instrumentalness', 'liveness', 'valence', 'tempo'
]
categories = 'activity'


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/renew_token/<path:telegram_user>', methods=['GET'])
def renew_token(telegram_user):
    manager = DatabaseManager(DATABASE)
    user = manager.get_user_by_telegram_id(telegram_user, access_token=True)
    new_token = get_new_token(user['refresh_token'])

    if 'error' not in new_token:
        manager.update_token(telegram_user, new_token)

        return jsonify({
            'code': 1,
            'message': 'New token created.'
        })
    else:
        return jsonify(new_token)


@app.route('/connect/<path:telegram_user>/<path:telegram_first_name>', methods=['GET'])
def connect(telegram_user, telegram_first_name):
    session['telegram_user'] = telegram_user
    session['telegram_first_name'] = telegram_first_name

    url = 'https://accounts.spotify.com/authorize/?client_id={}&redirect_uri={}&response_type=code&scope=playlist-read-private'
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
            user_info = resp.json()

            manager = DatabaseManager(DATABASE)
            manager.create_user(
                session['telegram_user'],
                session['telegram_first_name'],
                user_info['id'],
                access_token,
                refresh_token
            )

    return redirect('/')


@app.route('/api/v1/artist/<path:artist_name>', methods=['GET'])
def artist(artist_name):
    url = 'https://api.spotify.com/v1/search?q={}&type=artist'
    resp = requests.get(
        url=url.format(artist_name)
    )

    return jsonify(json.loads(resp.content))


@app.route('/api/v1/song/<path:song_name>', methods=['GET'])
def song(song_name):
    url = 'https://api.spotify.com/v1/search?q={}&type=track'
    resp = requests.get(
        url=url.format(song_name)
    )
    return jsonify(json.loads(resp.content))


@app.route('/api/v1/song_predicted/<path:telegram_user>/<path:song_name>', methods=['GET'])
def song_predicted(telegram_user, song_name):
    manager = DatabaseManager(DATABASE)
    user = manager.get_user_by_telegram_id(telegram_user, access_token=True)

    url = 'https://api.spotify.com/v1/search?q={}&type=track'
    resp = requests.get(
        url=url.format(song_name)
    )

    tracks = resp.json()['tracks']['items']
    clf = joblib.load(PICKLE)

    output = []
    for track in tracks:
        track_data = {
            'name': track['name'],
            'popularity': track['popularity'],
            'artists': ','.join(a['name'] for a in track['artists']),
            'album_name': track['album']['name'],
            'thumb': track['album']['images'][0]['url'] if track['album']['images'] else None,
            'external_url': track['external_urls']['spotify']
        }

        track_features = get_track_features(track['id'], user['access_token'])

        if track_features:
            track_features_serie = {x: track_features[x] for x in features}
            df = pd.DataFrame.from_records(track_features_serie, index=[0])
            prediction = clf.predict(df)

            track_data['activity'] = prediction[0] if prediction and len(prediction) else None

        output.append(track_data)

    return jsonify(output)


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


@app.route('/api/v1/update_pickle/<path:telegram_user>', methods=['GET'])
def update_pickle(telegram_user):
    manager = DatabaseManager(DATABASE)
    df = manager.get_classified_songs(telegram_user)

    for column in features:
        df[column] = df[column].apply(lambda x: 0 if x == 'NA' else x)

    clf = svm.SVC()
    clf.fit(
        df[features],
        df[categories]
    )

    joblib.dump(clf, PICKLE)

    return jsonify({'code': 1, 'trained': len(df)})


@app.route('/api/v1/get_playlists_songs/<path:telegram_user>/', methods=['GET'])
def get_playlists_songs(telegram_user):
    manager = DatabaseManager(DATABASE)
    user = manager.get_user_by_telegram_id(telegram_user, access_token=True)

    url = 'https://api.spotify.com/v1/me/playlists'
    resp = requests.get(
        url=url,
        headers={
            'Authorization': user['access_token']
        }
    )
    playlists = resp.json()['items']

    saved_songs = 0
    for playlist in playlists:
        tracks = get_playlist_tracks_info(playlist['owner']['id'], playlist['id'], user['access_token'])
        manager.add_songs(
            user['id'],
            tracks
        )
        saved_songs += len(tracks)

    return jsonify({
        'code': 1,
        'saved_songs': saved_songs
    })


def get_new_token(refresh_token):
    url = 'https://accounts.spotify.com/api/token'

    resp = requests.post(
        url=url,
        data={
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }
    )

    if resp.status_code != 200:
        return resp.json()

    else:
        token = resp.json()
        return '%s %s' % (token['token_type'], token['access_token'])


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


def get_playlist_tracks_info(playlist_owner, playlist_id, access_token):
    url = 'https://api.spotify.com/v1/users/{}/playlists/{}/tracks'

    tracks = []
    next_batch = None
    while True:
        next_url = next_batch if next_batch else url.format(playlist_owner, playlist_id)
        resp = requests.get(
            url=next_url,
            headers={
                'Authorization': access_token
            }
        )

        for item in [x['track'] for x in resp.json()['items']]:
            track_features = get_track_features(item['id'], access_token)
            tracks.append({
                'track_id': item['id'],
                'track_name': item['name'],
                'track_artists': [x['name'] for x in item['artists']],
                'track_popularity': item['popularity'],
                'track_album_id': item['album']['id'],
                'track_album_name': item['album']['name'],

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
            })

        if 'next' not in resp.json() or not resp.json()['next']:
            break

        else:
            next_batch = resp.json()['next']

    return tracks

if __name__ == '__main__':
    app.run(
        host='127.0.0.1',
        debug=True
    )
