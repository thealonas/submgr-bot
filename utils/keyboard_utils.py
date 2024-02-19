from telegram import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

import phrases
from utils.callback_utils import CallbackList


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [phrases.main_menu_active, phrases.main_menu_available],
            [phrases.main_menu_profile],
        ],
        resize_keyboard=True,
    )


def no_elements_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[no_elements_button]])


no_elements_button = InlineKeyboardButton(
    "🤷‍♀️ тут пусто", callback_data=CallbackList.no_elements
)
