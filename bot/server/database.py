import datetime
import pandas as pd
import os
import sqlite3


class DatabaseManager:
    _DATABASE = None

    def __init__(self, database_path):
        if not os.path.exists(database_path):
            conn = sqlite3.connect(database_path)
            c = conn.cursor()

            c.execute("""
              CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                telegram_user_id TEXT UNIQUE,
                telegram_first_name TEXT UNIQUE,
                registered_on DATE,

                spotify_id TEXT UNIQUE,
                access_token TEXT,
                refresh_token TEXT
              )
            """)

            c.execute("""
                CREATE TABLE songs (
                    id INTEGER PRIMARY KEY,
                    spotify_id TEXT UNIQUE,
                    name TEXT,
                    album_id TEXT,
                    album_name TEXT,
                    popularity INTEGER,
                    duration INTEGER,
                    danceability FLOAT,
                    energy FLOAT,
                    key FLOAT,
                    loudness FLOAT,
                    mode FLOAT,
                    speechiness FLOAT,
                    acousticness FLOAT,
                    instrumentalness FLOAT,
                    liveness FLOAT,
                    valence FLOAT,
                    tempo FLOAT,
                    activity INTEGER
                )
            """)

            c.execute("""
                CREATE TABLE artists (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE
                )
            """)

            c.execute("""
                CREATE TABLE song_artist (
                    song_id INTEGER,
                    artist_id INTEGER
                )
            """)

            c.execute("""
                CREATE TABLE song_user (
                    song_id INTEGER,
                    user_id INTEGER
                )
            """)

            conn.commit()
            conn.close()

        self._DATABASE = database_path

    def get_user_by_telegram_id(self, telegram_id, access_token=False):
        conn = sqlite3.connect(self._DATABASE)
        cursor = conn.execute("select * from users where telegram_user_id = \"%s\"" % telegram_id)
        resp = cursor.fetchone()
        conn.close()

        if resp:
            return {
                'id': resp[0],
                'telegram_user_id': resp[1],
                'telegram_first_name': resp[2],
                'registered_on': resp[3],
                'spotify_id': resp[4],
                'access_token': resp[5] if access_token else None,
                'refresh_token': resp[6] if access_token else None
            }

        else:
            return None

    def create_user(self, telegram_id, telegram_first_name, spotify_id, token, refresh_token):
        conn = sqlite3.connect(self._DATABASE)
        try:
            last_id = conn.execute(
                """
                  INSERT INTO users (
                    telegram_user_id, telegram_first_name, registered_on, spotify_id, access_token, refresh_token
                  )
                  VALUES (?, ?, ?, ?, ?, ?)""", (
                    telegram_id,
                    telegram_first_name,
                    datetime.datetime.now(),
                    spotify_id,
                    token,
                    refresh_token,
                )
            )
            conn.commit()
        except sqlite3.IntegrityError:
            last_id = conn.execute(
                """
                  UPDATE users SET access_token = ?, refresh_token = ? WHERE telegram_user_id = ?
                """, (
                    token,
                    refresh_token,
                    telegram_id,
                )
            )
            conn.commit()

        conn.close()

        return last_id

    def update_token(self, telegram_id, new_token):
        conn = sqlite3.connect(self._DATABASE)
        sql = """UPDATE users SET access_token=? WHERE telegram_user_id=?"""
        conn.execute(sql, (new_token, telegram_id))
        conn.commit()
        resp = conn.total_changes
        conn.close()

        return resp

    def get_unclassified_songs(self, telegram_id):
        conn = sqlite3.connect(self._DATABASE)

        sql = """
            SELECT
                s.id, s.name, s.album_name, s.popularity, a.name
            FROM users u, song_user su,  songs s, artists a, song_artist sa
            WHERE
                u.telegram_user_id = ? AND
                su.user_id = u.id AND
                su.song_id = s.id AND
                s.activity IS NULL AND
                sa.song_id = s.id AND
                sa.artist_id = a.id
            ORDER BY RANDOM()
            LIMIT 1
        """
        cursor = conn.execute(sql, (telegram_id,))
        resp = cursor.fetchone()
        conn.close()

        return resp

    def add_songs(self, user_id, tracks):
        conn = sqlite3.connect(self._DATABASE)
        with conn:
            for track in tracks:
                try:
                    cursor = conn.execute(
                        """
                          insert into songs(
                            spotify_id, name, album_id, album_name, popularity,
                            duration, danceability, energy, key, loudness, mode, speechiness, acousticness,
                            instrumentalness, liveness, valence, tempo
                          ) values (
                            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                          )""", (
                            track['track_id'],
                            track['track_name'],
                            track['track_album_id'],
                            track['track_album_name'],
                            track['track_popularity'],
                            track['duration'],
                            track['danceability'],
                            track['energy'],
                            track['key'],
                            track['loudness'],
                            track['mode'],
                            track['speechiness'],
                            track['acousticness'],
                            track['instrumentalness'],
                            track['liveness'],
                            track['valence'],
                            track['tempo'],
                        )
                    )

                    track_id = cursor.lastrowid
                    for artist in track['track_artists']:
                        try:
                            cursor.execute(
                                "insert into artists(name) values (?)", (
                                    artist,
                                )
                            )
                            artist_id = cursor.lastrowid

                        except sqlite3.IntegrityError:
                            cursor.execute("select id from artists where name = \"%s\"" % artist)
                            artist_id = cursor.fetchone()[0]

                        cursor.execute(
                            "insert into song_artist(song_id, artist_id) values (?, ?)", (
                                track_id,
                                artist_id
                            )
                        )

                    cursor.execute(
                        "insert into song_user(song_id, user_id) values (?, ?)", (
                            track_id,
                            user_id
                        )
                    )

                except sqlite3.IntegrityError:
                    print 'ignoring %s' % track

    def classify_song(self, track_id, activity):
        conn = sqlite3.connect(self._DATABASE)
        sql = """UPDATE songs SET activity=? WHERE id=?"""
        conn.execute(sql, (activity, track_id))
        conn.commit()
        resp = conn.total_changes
        conn.close()

        return resp

    def stats(self, telegram_id):
        conn = sqlite3.connect(self._DATABASE)

        sql = """
            select count(*)
            from songs s, song_user su, users u
            where
                s.activity is not null and
                s.id = su.song_id and
                su.user_id = u.id and
                u.telegram_user_id = ?
        """
        cursor = conn.execute(sql, (telegram_id,))
        total_classified = cursor.fetchone()[0]

        sql = """
                    select count(*)
                    from songs s, song_user su, users u
                    where
                        s.activity is null and
                        s.id = su.song_id and
                        su.user_id = u.id and
                        u.telegram_user_id = ?
                """
        cursor = conn.execute(sql, (telegram_id,))
        total_songs = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total_songs,
            'classified': total_classified
        }

    def get_classified_songs(self, telegram_id):
        conn = sqlite3.connect(self._DATABASE)
        sql = """
              SELECT
                danceability, energy, loudness, speechiness, acousticness,
                instrumentalness, liveness, valence, tempo, activity
              FROM songs s, users u, song_user su
              WHERE
                activity IS NOT NULL AND
                s.id = su.song_id AND
                su.user_id = u.id AND
                u.telegram_user_id = {}
        """.format(telegram_id)
        resp = pd.read_sql_query(sql, conn)
        conn.close()

        return resp
