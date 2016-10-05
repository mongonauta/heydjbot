#!/usr/bin/env python
# -*- coding: utf-8 -*-
import logging

from telegram import ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, ConversationHandler, RegexHandler

from local_secrets import TELEGRAM_TOKEN

GENRE_KEYBOARD = [['Heavy', 'Rap', 'Reagueton', u'Música Clásica']]
START, GENRE_SELECTOR = range(2)

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
        '/conversar - Charlamos?.\n'
    )

    return None


def cancel_conversation(bot, update):
    logger.info('cancel conversation')
    update.message.reply_text('Hasta luego! Encantado de conversar contigo.')

    return ConversationHandler.END


def chat(bot, update):
    user = update.message.from_user
    logger.info('chat - %s' % user)

    update.message.reply_text(
        "Sobre que quieres hablar?",
        reply_markup=ReplyKeyboardMarkup(
            GENRE_KEYBOARD,
            one_time_keyboard=True,
            resize_keyboard=True
        )
    )

    return GENRE_SELECTOR


def genre(bot, update):
    user = update.message.from_user
    genre_selected = update.message.text
    logger.info('genre (%s) - selected %s' % (user, genre_selected))

    if genre_selected == GENRE_KEYBOARD[0][0]:
        update.message.reply_text(u'Lo siento pero no me gusta la música satánica')

    elif genre_selected == GENRE_KEYBOARD[0][1]:
        update.message.reply_text(u'Lo siento pero no me gusta llevar los pantalones cagaos')

    elif genre_selected == GENRE_KEYBOARD[0][2]:
        update.message.reply_text(u'Mi creador me ha dicho (y cito) que deberías visitar a un buen psicólogo')

    elif genre_selected == GENRE_KEYBOARD[0][3]:
        update.message.reply_text(u'ZZZZZZZZZZZZZZZZZ')

    return ConversationHandler.END


def main():
    updater = Updater(TELEGRAM_TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('help', show_help))

    dp.add_handler(ConversationHandler(
        entry_points=[CommandHandler('conversar', chat)],
        states={
            GENRE_SELECTOR: [
                RegexHandler(u'^(%s|%s|%s|%s)$' % tuple(GENRE_KEYBOARD[0]), genre)
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
