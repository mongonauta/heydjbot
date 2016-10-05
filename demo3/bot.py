#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging
import requests

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, ConversationHandler, RegexHandler

from local_secrets import TELEGRAM_TOKEN, API_SERVER

NAVIGATION_KEYBOARD = ['ANTERIOR', 'SIGUIENTE']
ACTIVITY_KEYBOARD = [['WORK', 'RUN', 'TRAVEL', 'RELAX', 'PARTY']]

START, ACTIVITY_SELECTOR = range(2)
SHOW_SONG, SAVE_SONG = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def show_help(bot, update):
    logger.info('show_help...')

    update.message.reply_text(
        'Hola Humano! Soy el mejor DJ del mundo. \n\n'
        'Estas son las cosas que puedo hacer por ti:\n\n'
        '/help - Lo que estas leyendo.\n'
        '/train - Para categorizar canciones.\n'
        '/conectar - Para conectar con tu cuenta de Spotify.\n'
        '/playlist - Para crear una playlist en Spotify.\n'
    )

    return None


def cancel_conversation(bot, update):
    logger.info('cancel conversation')
    update.message.reply_text('Hasta luego! Encantado de conversar contigo.')

    return ConversationHandler.END


def connect(bot, update):
    user = update.message.from_user
    logger.info('connect %s' % user)

    resp = requests.get(
        url='{}/user_info/{}/'.format(API_SERVER, user.id)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Error connecting to the server.')

    # elif resp.json:
    #     update.message.reply_text('Don\'t piss me {}. You just really now me.'.format(user.first_name))

    else:
        update.message.reply_text(
            'Please, visit this website to connect your Spotify account.\n'
            '{}/connect/{}/{}/'.format(API_SERVER, user.id, user.first_name.replace(' ', '%20'))
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
                reply_markup=ReplyKeyboardMarkup(ACTIVITY_KEYBOARD, one_time_keyboard=True, resize_keyboard=True)
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
                ACTIVITY_KEYBOARD[0].index(update.message.text)
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


def choose_activity(bot, update):
    user = update.message.from_user
    logger.info('choose_activity - %s' % user)

    update.message.reply_text(
        "Que tipo de playlist quieres?",
        reply_markup=ReplyKeyboardMarkup(
            ACTIVITY_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    return ACTIVITY_SELECTOR


def create_playlist(bot, update):
    user = update.message.from_user
    activity_selected = update.message.text
    logger.info('create_playlist (%s) - selected %s' % (user, activity_selected))

    activity_id = ACTIVITY_KEYBOARD[0].index(activity_selected)
    resp = requests.get(
        url='{}/create_playlist/{}/{}/'.format(API_SERVER, user.id, activity_id)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text(
            'Sorry {}, but I can\'t do that. Please, use "connect" command'.format(user['first_name'])
        )

    else:
        resp = json.loads(resp.content)
        if resp['code'] == 0:
            update.message.reply_text(
                'Playlist creada. Disfruta!!!!\n Resp:\n %s' % (resp.json())
            )

        else:
            update.message.reply_text(resp['message'])

    return ConversationHandler.END


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('help', show_help))
    dp.add_handler(CommandHandler('conectar', connect))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('playlist', choose_activity)],
        states={
            ACTIVITY_SELECTOR: [
                RegexHandler(u'^(%s|%s|%s|%s|%s)$' % tuple(ACTIVITY_KEYBOARD[0]), create_playlist)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('train', train)],
        states={
            SAVE_SONG: [
                CommandHandler('cancel', cancel_conversation),
                RegexHandler('^(%s)$' % NAVIGATION_KEYBOARD[1], train),
                RegexHandler('^(%s)$' % '|'.join(ACTIVITY_KEYBOARD[0]), save_classification)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    ))

    dp.add_error_handler(error)

    updater.start_polling()
    logger.info('Listening...')

    updater.idle()


if __name__ == '__main__':
    main()
