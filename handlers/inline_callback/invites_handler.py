import datetime

from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import phrases
from database_models.invite import Invite
from models.bot_context import BotContext
from utils.callback_utils import ConfigurableCallbackList, CallbackList
from utils.datetime_utils import DateTimeUtils


async def handle_invites_callback(ctx: BotContext, query_data: str) -> bool:
    """
    возвращает can_continue
    """
    if ConfigurableCallbackList.invite_overview.matches(query_data):
        invite = ConfigurableCallbackList.invite_overview.extract_value(query_data)
        return await overview(ctx, invite)

    return True


async def overview(ctx: BotContext, invite_id: str) -> bool:
    """
    возвращает can_continue
    """
    invites = Invite.find(Invite.id == invite_id).all()

    if not invites:
        await ctx.answer_callback("этот инвайт недоступен 🚫")
        return False

    invite = invites[0]

    if invite.used:
        await ctx.answer_callback("этот инвайт был использован ⚠️")
        return False

    if invite.spoiled:
        await ctx.answer_callback("этот инвайт просрочен ⏰")
        return False

    message = (
        f"<b>🔗 инвайт №{invite.id}</b>\n\n<b>приглашение:</b> <code>{invite.get_url()}</code>\n"
        f"<b>действительно до:</b> "
        f"{DateTimeUtils.day_and_month_in_words(invite.issue_date + datetime.timedelta(days=2))}"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(phrases.go_back, callback_data=CallbackList.invites)]]
    )

    await ctx.update_message(message, reply=keyboard)
    return False
