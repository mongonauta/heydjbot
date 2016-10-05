#!/usr/bin/env python
# -*- coding: utf-8 -*-
import json
import logging
import requests

from telegram.ext import Updater, CommandHandler, ConversationHandler, RegexHandler

from local_secrets import TELEGRAM_TOKEN

SELECTED = 1

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
        '/artista - Buscar artista.\n'
        '/cancion - Buscar cancion.\n'
    )

    return None


def cancel_conversation(bot, update):
    user = update.message.from_user
    logger.info('cancel conversation - %s' % user)
    update.message.reply_text('Hasta luego, %s! Encantado de conversar contigo.' % user.first_name)

    return ConversationHandler.END


def artist(bot, update):
    user = update.message.from_user
    logger.info('artist for %s' % user)
    update.message.reply_text('Sobre que artista quieres que busque?')

    return SELECTED


def search_artist(bot, update):
    user = update.message.from_user
    artist_name = update.message.text
    logger.info('search_artist for user %s and artist name %s' % (user, artist_name))

    url = 'https://api.spotify.com/v1/search?q={}&type=artist'
    resp = requests.get(
        url=url.format(artist_name)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Lo siento pero lo que estás buscando es demasiado raro incluso para Spotify')
        return ConversationHandler.END

    else:
        artist_list = json.loads(resp.content)['artists']['items']

        update.message.reply_text(u"""{} (Popularidad% {})\n{}\n{}""".format(
            artist_list[0]['name'],
            artist_list[0]['popularity'],
            artist_list[0]['images'][0]['url'] if 'images' in artist_list[0] and artist_list[0]['images'] else None,
            artist_list[0]['external_urls']['spotify'],
        ))

    return ConversationHandler.END


def song(bot, update):
    user = update.message.from_user
    logger.info('song for %s' % user)
    update.message.reply_text('Que canción quieres que busque?')

    return SELECTED


def search_song(bot, update):
    user = update.message.from_user
    song_name = update.message.text
    logger.info('search_song for user %s and song name %s' % (user, song_name))

    url = 'https://api.spotify.com/v1/search?q={}&type=track'
    resp = requests.get(
        url=url.format(song_name)
    )

    if resp.status_code != 200 or not resp.json():
        update.message.reply_text('Lo siento pero lo que estás buscando es demasiado raro incluso para Spotify')
        return ConversationHandler.END

    else:
        song_list = json.loads(resp.content)['tracks']['items']

        update.message.reply_text(
            u"""{} (Popularidad% {})\nAlbum: {}\nArtistas: {}\n{}\n{}""".format(
                song_list[0]['name'],
                song_list[0]['popularity'],
                song_list[0]['album']['name'],
                ', '.join(a['name'] for a in song_list[0]['artists']),
                song_list[0]['album']['images'][0]['url'] if song_list[0]['album']['images'] else None,
                song_list[0]['external_urls']['spotify'],
            )
        )

    return ConversationHandler.END


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('help', show_help))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('artista', artist)],
        states={
            SELECTED: [
                RegexHandler(u'.*', search_artist)
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    ))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('cancion', song)],
        states={
            SELECTED: [
                RegexHandler(u'.*', search_song)
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
