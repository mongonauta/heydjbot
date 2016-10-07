#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging
import requests

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, ConversationHandler, RegexHandler

from local_secrets import TELEGRAM_TOKEN, API_SERVER

SONG_KEYBOARD = [['SAVE', 'IGNORE']]
ACTIVITY_KEYBOARD = [['WORK', 'RUN', 'TRAVEL', 'RELAX', 'PARTY']]

SHOW_SONG, SONG_ACTION = range(2)

START, ACTIVITY_SELECTOR = range(2)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)


def error(bot, update, error):
    logger.warn('Update "%s" caused error "%s"' % (update, error))


def show_help(bot, update):
    user = update.message.from_user
    logger.info('show_help for %s' % user)

    update.message.reply_text(
        'Hola Humano! Soy el mejor DJ del mundo. \n\n'
        'Estas son las cosas que puedo hacer por ti:\n\n'
        '/help - Lo que estas leyendo.\n'
        '/conectar - Para conectar con tu cuenta de Spotify.\n'
        '/cancion - Buscar cancion.\n'
        '/playlist - Para crear una playlist en Spotify.\n'
    )

    return None


def cancel_conversation(bot, update):
    user = update.message.from_user
    logger.info('cancel conversation - %s' % user)
    update.message.reply_text('Hasta luego, %s! Encantado de conversar contigo.' % user.first_name)

    if bot.song_cache:
        bot.song_cache = None

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


def song(bot, update):
    user = update.message.from_user
    logger.info('song for %s' % user)
    bot.song_cache = None
    update.message.reply_text('Que canción quieres que busque?')

    return SHOW_SONG


def search_song(bot, update):
    user = update.message.from_user
    song_name = update.message.text
    logger.info('search_song for user %s and song name %s' % (user, song_name))

    url = '{}/song/{}'
    resp = requests.get(
        url=url.format(API_SERVER, song_name)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Lo siento pero lo que estás buscando es demasiado raro incluso para Spotify')
        return ConversationHandler.END

    else:
        song_list = json.loads(resp.content)

        update.message.reply_text(
            u"""{} (Popularidad% {})\nActividad: {}\nAlbum: {}\nArtistas: {}\n{}\n{}""".format(
                song_list[0]['track_name'],
                song_list[0]['track_popularity'],
                song_list[0]['activity'],
                song_list[0]['track_album_name'],
                ','.join(a['name'] for a in song_list[0]['artists']),
                song_list[0]['thumb'],
                song_list[0]['external_url'],
            ),
            reply_markup=ReplyKeyboardMarkup(
                SONG_KEYBOARD,
                one_time_keyboard=True,
                resize_keyboard=True
            )
        )

        bot.song_cache = song_list[0]

    return SONG_ACTION


def save_song(bot, update):
    user = update.message.from_user
    action = update.message.text
    logger.info('save_song for user %s and action %s' % (user, save_song))

    if action == SONG_KEYBOARD[0][0] and bot.song_cache:
        song_to_save = bot.song_cache
        song_to_save['artists'] = ','.join(a['name'] for a in song_to_save['artists'])
        resp = requests.post(
            '{}/save_song/{}'.format(API_SERVER, user.id),
            data=song_to_save
        )

        if resp.status_code != 200 or not resp.json():
            update.message.reply_text('Error connecting to the server.')

        else:
            update.message.reply_text(resp.json()['message'])

    else:
        update.message.reply_text(u'Vale, la canción no te ha gustado.\nPrueba otra vez con /cancion')

    bot.song_cache = None
    return ConversationHandler.END


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
        entry_points=[CommandHandler('cancion', song)],
        states={
            SHOW_SONG: [
                RegexHandler(u'.*', search_song)
            ],
            SONG_ACTION: [
                RegexHandler(u'^(%s|%s)$' % tuple(SONG_KEYBOARD[0]), save_song)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('playlist', choose_activity)],
        states={
            ACTIVITY_SELECTOR: [
                RegexHandler(u'^(%s|%s|%s|%s|%s)$' % tuple(ACTIVITY_KEYBOARD[0]), create_playlist)
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
