#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

import requests
from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, RegexHandler, ConversationHandler

from common.secrets import TELEGRAM_TOKEN

# FLASK SERVER ROOT
API_SERVER = 'http://127.0.0.1:5000/api/v1'
PICKLE = 'activities.pickle'

# ACTIVITY TAGS
WORK, RUN, TRAVEL, RELAX, PARTY, SHIT = range(6)

# NAVIGATION STATES AND KEYBOARDS
NAVIGATION_KEYBOARD = ['Previous', 'Next']
ACTIVITIES_KEYBOARD = [['WORK', 'RUN', 'TRAVEL', 'RELAX', 'PARTY', 'SHIT']]

SHOW_SONG, SAVE_SONG = range(2)
START, NAVIGATE = range(2)

# SPOTIFY TEMPLATES
ARTIST_TEMPLATE = u"""
{} (Popularity% {})\n
{}
{}
"""
SONG_TEMPLATE = u"""
{} (Popularity% {})\n
Recommended Activity: {}
Artists: {}\n
Album: {}\n
{}
{}
"""


# CACHES
result_search_cache = {
    'items': [],
    'current_position': 0
}


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


# #############################################################################
# BASIC COMMANDS
# #############################################################################
def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def start(bot, update):
    logger.info('start... (%s)' % update.message.text)

    update.message.reply_text(
        'Hi, Human! I\'m the best DJ in the world.\n\n'
        'If you want to know what can I do for you, type /help.'
    )

    return None


def show_help(bot, update):
    logger.info('show_help...')

    update.message.reply_text(
        'Hi Human! I\'m the best DJ in the world. \n\n'
        'These are the things I can do for you:\n\n'
        '/help - to show this help.\n'

        '/artist - to search an artist.\n'
        '/song - to search a song.\n'

        '/connect - connect your Spotify connection.\n'
        '/train - to talk about the music you like.\n'
        '/sync - to update predictions with new training.\n'
    )

    return None


# #############################################################################
# DATABASE COMMANDS
# #############################################################################
def connect(bot, update):
    user = update.message.from_user
    logger.info('connect %s' % user)

    resp = requests.get(
        url='{}/user_info/{}/'.format(API_SERVER, user.id)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Error connecting to the server.')

    elif resp.json:
        update.message.reply_text('Don\'t piss me {}. You just really now me.'.format(user.first_name))

    else:
        update.message.reply_text(
            'Please, visit this website to connect your Spotify account.\n'
            '{}/connect/{}/{}'.format(API_SERVER, user.id, user.first_name)
        )

    return None


def train(bot, update):
    user = update.message.from_user
    logger.info('show_song_to_clasify %s' % user)

    resp = requests.get(
        url='{}/user_info/{}/'.format(API_SERVER, user.id)
    )

    if not resp.json():
        update.message.reply_text(
            'Sorry {}, but I can\'t do that. Please, use "connect" command'.format(user['first_name'])
        )

    else:
        resp = requests.get(
            url='{}/train/{}/'.format(API_SERVER, user.id)
        )

        song = resp.json()['song'] if 'song' in resp.json() else None
        if song:
            bot.song_cache = song
            update.message.reply_text(
                u"""
                    Choose one activity for this song:\n\n
                    Title: {}\n
                    Artist: {}\n
                    Album: {}\n
                """.format(song[1], song[4], song[2]),
                reply_markup=ReplyKeyboardMarkup(ACTIVITIES_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)
            )

        else:
            update.message.reply_text("Server error. %s" % resp.json())

    return SAVE_SONG


def save_classification(bot, update):
    user = update.message.from_user
    logger.info('save_classification(%s) %s - %s' % (user, bot.song_cache, update.message.text))

    resp = requests.get(
        url='{}/user_info/{}/'.format(API_SERVER, user.id)
    )

    if not resp.json():
        update.message.reply_text(
            'Sorry {}, but I can\'t do that. Please, use "connect" command'.format(user['first_name'])
        )

    else:
        resp = requests.get(
            url='{}/classify/{}/{}'.format(
                API_SERVER,
                bot.song_cache[0],
                ACTIVITIES_KEYBOARD[0].index(update.message.text)
            )
        )

        result = resp.json()
        resp = requests.get(
            url='{}/stats/{}/'.format(
                API_SERVER,
                user.id
            )
        )
        result['total'] = resp.json()['total']
        result['classified'] = resp.json()['classified']

        update.message.reply_text(
            'Result: %s \n\n Statistics:\n %s' % (result, resp.json()),
            reply_markup=ReplyKeyboardMarkup([[NAVIGATION_KEYBOARD[1]]], one_time_keyboard=True, resize_keyboard=True)
        )
    return SAVE_SONG


def update_pickle(bot, update):
    user = update.message.from_user
    logger.info('update_pickle %s' % user)

    resp = requests.get(url='{}/update_pickle/{}'.format(API_SERVER, user.id))
    update.message.reply_text('Result: %s' % resp.json())
    return None

# #############################################################################
# NAVIGATION COMMANDS
# #############################################################################


def navigate(bot, update):
    logger.info('navigate...')
    if update.message.text == NAVIGATION_KEYBOARD[0]:
        result_search_cache['current_position'] -= 1
    else:
        result_search_cache['current_position'] += 1

    if result_search_cache['current_position'] <= 0:
        result_search_cache['current_position'] = 0

    if result_search_cache['current_position'] >= len(result_search_cache['items']):
        result_search_cache['current_position'] = len(result_search_cache['items']) - 1

    if result_search_cache['current_position'] == 0:
        keyboard = [NAVIGATION_KEYBOARD[1]]

    elif result_search_cache['current_position'] == len(result_search_cache['items']) - 1:
        keyboard = [NAVIGATION_KEYBOARD[0]]

    else:
        keyboard = NAVIGATION_KEYBOARD

    update.message.reply_text(
        result_search_cache['items'][result_search_cache['current_position']],
        reply_markup=ReplyKeyboardMarkup([keyboard], one_time_keyboard=True)
    )
    return NAVIGATE


def cancel_navigation(bot, update):
    logger.info('cancel navigation')
    update.message.reply_text('Bye! I hope we can talk again some day.')
    bot.song_cache = song

    return ConversationHandler.END


# #############################################################################
# START SPOTIFY
# #############################################################################


def artist(bot, update):
    logger.info('artist...')
    update.message.reply_text('Please, type the name of the artist')

    return START


def search_artist(bot, update):
    artist_name = update.message.text
    logger.info('search_artist %s' % artist_name)

    resp = requests.get(
        url='{}/artist/{}'.format(API_SERVER, artist_name)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Sorry, you are searching a really strange band for Spotify')
        return ConversationHandler.END

    elif len(resp.json()['artists']['items']) == 1:
        x = resp.json()['artists']['items'].pop()
        update.message.reply_text(
            ARTIST_TEMPLATE.format(
                x['name'],
                x['popularity'],
                x['images'][0]['url'] if 'images' in x and x['images'] else None,
                x['external_urls']['spotify']
            )
        )
        return ConversationHandler.END

    else:
        result_search_cache['current_position'] = 0
        result_search_cache['items'] = []

        for x in resp.json()['artists']['items']:
            result_search_cache['items'].append(
                ARTIST_TEMPLATE.format(
                    x['name'],
                    x['popularity'],
                    x['images'][0]['url'] if 'images' in x and x['images'] else None,
                    x['external_urls']['spotify']
                )
            )

        keyboard = [NAVIGATION_KEYBOARD[1:]]
        update.message.reply_text(
            result_search_cache['items'][0],
            reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        )
        return NAVIGATE


def song(bot, update):
    logger.info('song...')
    update.message.reply_text('Please, type the name of the song')

    return START


def search_song(bot, update):
    user = update.message.from_user
    song_name = update.message.text

    logger.info('search_song %s - %s' % (user, song_name))
    resp = requests.get(
        url='{}/user_info/{}/'.format(API_SERVER, user.id)
    )

    if not resp.json():
        update.message.reply_text(
            'Sorry {}, but I can\'t do that. Please, use "connect" command'.format(user['first_name'])
        )

    else:
        resp = requests.get(
            url='{}/song_predicted/{}/{}'.format(API_SERVER, user.id, song_name)
        )

        if resp.status_code != 200 or not resp.json():
            update.message.reply_text('Sorry, you are searching a really strange song for Spotify')
            return ConversationHandler.END

        elif len(resp.json()) == 1:
            x = resp.json().pop()
            if 'activity' in x:
                activity = ACTIVITIES_KEYBOARD[0][x['activity']]
            else:
                activity = 'NA'

            update.message.reply_text(
                SONG_TEMPLATE.format(
                    x['name'],
                    x['popularity'],
                    activity,
                    x['artists'],
                    x['album_name'],
                    x['thumb'],
                    x['external_url']
                )
            )
            return ConversationHandler.END

        else:
            result_search_cache['current_position'] = 0
            result_search_cache['items'] = []

            for x in resp.json():
                if 'activity' in x:
                    activity = ACTIVITIES_KEYBOARD[0][x['activity']]
                else:
                    activity = 'NA'

                result_search_cache['items'].append(
                    SONG_TEMPLATE.format(
                        x['name'],
                        x['popularity'],
                        activity,
                        x['artists'],
                        x['album_name'],
                        x['thumb'],
                        x['external_url']
                    )
                )

            keyboard = [NAVIGATION_KEYBOARD[1:]]
            update.message.reply_text(
                result_search_cache['items'][0],
                reply_markup=ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            )
            return NAVIGATE


# #############################################################################
# END SPOTIFY BLOCK
# #############################################################################


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('help', show_help))
    dp.add_handler(CommandHandler('connect', connect))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('artist', artist)],
        states={
            START: [
                CommandHandler('cancel', cancel_navigation),
                RegexHandler('.*', search_artist)
            ],
            NAVIGATE: [
                RegexHandler('^(%s|%s)$' % (NAVIGATION_KEYBOARD[0], NAVIGATION_KEYBOARD[1]), navigate)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_navigation)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('song', song)],
        states={
            START: [
                CommandHandler('cancel', cancel_navigation),
                RegexHandler('.*', search_song)
            ],
            NAVIGATE: [
                RegexHandler('^(%s|%s)$' % (NAVIGATION_KEYBOARD[0], NAVIGATION_KEYBOARD[1]), navigate)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_navigation)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('train', train)],
        states={
            SAVE_SONG: [
                CommandHandler('cancel', cancel_navigation),
                RegexHandler('^(%s)$' % NAVIGATION_KEYBOARD[1], train),
                RegexHandler('^(%s)$' % '|'.join(ACTIVITIES_KEYBOARD[0]), save_classification)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_navigation)]
    ))

    dp.add_handler(CommandHandler('sync', update_pickle))

    dp.add_handler(RegexHandler('.*', start))

    dp.add_error_handler(error)

    updater.start_polling()
    logger.info('Listening...')

    updater.idle()


if __name__ == '__main__':
    main()
