#!/usr/bin/env python
# -*- coding: utf-8 -*-
import pandas as pd
import pickle
import sqlite3

from sklearn import svm

from bot.server.settings.local_credentials import DATABASE

ACTIVITIES = ['WORK', 'RUN', 'TRAVEL', 'RELAX', 'PARTY', 'SHIT']

features = [
    'danceability', 'energy', 'loudness', 'speechiness', 'acousticness',
    'instrumentalness', 'liveness', 'valence', 'tempo', 'activity'
]
categories = 'activity'


def get_trained_songs(offset, limit, only_features=True):
    conn = sqlite3.connect('server/%s' % DATABASE)

    sql = """
          SELECT {}
          FROM songs
          WHERE activity IS NOT NULL
          LIMIT {}, {}
        """.format(
            ','.join(features) if only_features else '*',
            offset,
            limit
        )
    df = pd.read_sql_query(sql, conn)

    conn.close()

    for column in features:
        df[column] = df[column].apply(lambda x: 0 if x == 'NA' else x)

    return df


def main():
    df_train = get_trained_songs(0, 450)
    clf = svm.SVC()
    clf.fit(
        df_train[features],
        df_train[categories]
    )

    df_test = get_trained_songs(450, 50, only_features=False)
    data_to_predict = df_test[features]

    predictions = clf.predict(data_to_predict)
    for track_index in range(len(df_test)):
        print df_test['name'][track_index], ACTIVITIES[predictions[track_index]]

if __name__ == '__main__':
    main()
