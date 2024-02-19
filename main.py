import logging
import os

import sentry_sdk
from redis_om import Migrator
from sentry_sdk.integrations.logging import LoggingIntegration
from telegram import Update, Bot
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

import phrases
from background_services.invoice_overwatch import InvoiceOverwatch
from background_services.invoice_service import InvoiceService
from background_services.reminder_service import ReminderService
from background_services.revolut_service import RevolutService
from background_services.spoiled_invites_service import SpoiledInvitesService
from background_services.spoiled_invoices_service import SpoiledInvoicesService
from database_models.user import User
from handlers.commands_handler import commands_handler
from handlers.inline_callback.common_callback_handler import handle_callbacks
from handlers.invite_handler import invite_handler
from handlers.menu_handler import menu_handler
from handlers.typing.typing_handler import typing_handler
from models.bot_context import BotContext
from utils import keyboard_utils

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.ERROR
)

sentry_logging = LoggingIntegration(
    level=logging.INFO,
    event_level=logging.ERROR,
)
sentry_sdk.init(
    dsn="https://60bdd7be86e447d0b0733c22ad749ae6@o555933.ingest.sentry.io/4505465475301376",
    integrations=[
        sentry_logging,
    ],
    traces_sample_rate=1.0,
)


def get_ctx(update: Update, context: ContextTypes.DEFAULT_TYPE) -> BotContext:
    ctx = BotContext(update, context, None)

    user = User.find(User.id == update.effective_user.id).all()
    if not user:
        ctx.user = None
    else:
        ctx.user = user[0]

    return ctx


async def main_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_ctx(update, context)

    # проверялка на инвайты
    if not await invite_handler(ctx):
        return

    # команды для админов
    if not await commands_handler(ctx):
        return

    # запрос на ввод
    if not await typing_handler(ctx):
        return

    # хэндл меню
    if not await menu_handler(ctx):
        return

    await ctx.context.bot.send_message(
        chat_id=ctx.update.effective_user.id,
        text=phrases.invalid_command,
        reply_markup=keyboard_utils.main_menu_keyboard(),
    )


async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ctx = get_ctx(update, context)

    # пошел нахуй
    if ctx.user is None:
        await ctx.answer_callback("ты не авторизирован 🤚")
        return

    # подписки, инвойсы, инвайты
    if not await handle_callbacks(ctx):
        return


def start_background_tasks(bot_obj: Bot):
    tasks = [
        InvoiceService(),
        ReminderService(bot_obj),
        InvoiceOverwatch(),
        SpoiledInvitesService(),
        SpoiledInvoicesService(),
        RevolutService(),
    ]

    for task in tasks:
        task.start()


if __name__ == "__main__":
    token = os.environ["TG_TOKEN"]

    Migrator().run()

    bot = Bot(token=token)

    start_background_tasks(bot)

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.ALL, main_handler))
    app.add_handler(CallbackQueryHandler(callback_query_handler))
    app.run_polling()
