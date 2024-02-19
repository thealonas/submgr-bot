from typing import Optional

import requests
from telegram import ReplyKeyboardMarkup
from telegram import Update, InlineKeyboardMarkup, ReplyKeyboardRemove, ForceReply
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import ContextTypes

from database_models.user import User


class BotContext:
    update: Update
    context: ContextTypes.DEFAULT_TYPE
    user: Optional[User]

    @staticmethod
    def can_use_image(logo: str) -> bool:
        return requests.get(logo).status_code == 200

    def __init__(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user: Optional[User] = None,
    ):
        self.update = update
        self.context = context
        self.user = user

    async def send_message(
        self,
        text: str,
        reply: (
            InlineKeyboardMarkup
            | ReplyKeyboardMarkup
            | ReplyKeyboardRemove
            | ForceReply
            | None
        ) = None,
        parse_mode: str = ParseMode.HTML,
        disable_web_page_preview: bool = True,
        chat_id: int | None = None,
    ):
        if chat_id is None:
            chat_id = self.update.effective_chat.id

        await self.context.bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=reply,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
        return

    async def delete_message(self, message_id: int = None):
        if message_id is None:
            message_id = self.update.effective_message.message_id
        try:
            await self.context.bot.delete_message(
                chat_id=self.update.effective_chat.id, message_id=message_id
            )
        except TelegramError:
            return

    async def update_message(
        self,
        text: str,
        reply: (
            InlineKeyboardMarkup
            | ReplyKeyboardMarkup
            | ReplyKeyboardRemove
            | ForceReply
            | None
        ) = None,
        disable_web_page_preview: bool = True,
        message_id: int = None,
    ):
        if message_id is None:
            message_id = self.update.effective_message.message_id
        try:
            await self.context.bot.edit_message_text(
                chat_id=self.update.effective_chat.id,
                message_id=message_id,
                text=text,
                reply_markup=reply,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=disable_web_page_preview,
            )
        except TelegramError:
            await self.delete_message(message_id)
            await self.send_message(
                text=text,
                reply=reply,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=disable_web_page_preview,
            )

    async def answer_callback(self, text: str, callback_id: str = None):
        if callback_id is None:
            callback_id = self.update.callback_query.id

        await self.context.bot.answer_callback_query(
            callback_query_id=callback_id, text=text
        )

    async def answer_callback_popout(self, text: str, callback_id: str = None):
        if callback_id is None:
            callback_id = self.update.callback_query.id

        await self.context.bot.answer_callback_query(
            callback_query_id=callback_id, text=text, show_alert=True
        )
