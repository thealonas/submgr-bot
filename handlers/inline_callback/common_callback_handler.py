import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import handlers.menu_handler
import phrases
from database_models.invite import Invite, life_time_in_days
from database_models.user import User
from enums.list_type import ListType
from handlers.inline_callback.configurable_callback_handler import (
    handle_configurable_callback,
)
from models.bot_context import BotContext
from modules.invite_module import InviteModule
from modules.invoice_module import InvoiceModule
from modules.subscription_module import SubscriptionModule
from utils.callback_utils import CallbackList
from utils.datetime_utils import DateTimeUtils


async def handle_callbacks(ctx: BotContext) -> bool:
    """
    Handling complex callbacks
    :param ctx: bot context
    :return: can continue
    """

    # MCB MainCallbackHandler шорткат для поиска в идее

    # всё из CallbackList кроме кнопочек навигации
    if not await handle_common_callbacks(ctx):
        return False

    # кнопочки навигации подписок
    if not await handle_subscriptions_pagination_buttons(ctx):
        return False

    # кнопочки навигации инвойсов
    if not await handle_invoices_pagination_buttons(ctx):
        return False

    # кнопочки навигации инвайтов
    if not await handle_invites_pagination_buttons(ctx):
        return False

    # всё из ConfigurableCallbackList
    if not await handle_configurable_callback(ctx):
        return False

    return True


async def handle_subscriptions_pagination_buttons(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """
    query = ctx.update.callback_query
    query_data = query.data
    callback_from_id = query.from_user.id

    match query_data:
        case (
            CallbackList.available_subs_list_pagination_forward
            | CallbackList.available_subs_list_pagination_backward
        ):
            list_type = ListType.AVAILABLE_SUBS
        case (
            CallbackList.my_subs_list_pagination_forward
            | CallbackList.my_subs_list_pagination_backward
        ):
            list_type = ListType.MY_SUBS
        case _:
            return True

    SubscriptionModule.handle_pagination_button_press(callback_from_id, query_data)

    subs = ctx.user.get_subs(list_type)

    new_keyboard = SubscriptionModule.generate_keyboard(
        subs, callback_from_id, list_type
    )

    text = query.message.text_html

    await ctx.update_message(
        text=text, message_id=query.message.message_id, reply=new_keyboard
    )

    return False


async def handle_invoices_pagination_buttons(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """
    query = ctx.update.callback_query
    callback_from_id = query.from_user.id
    user_invoices = ctx.user.get_invoices()

    match query.data:
        case CallbackList.invoices_pagination_forward:
            InvoiceModule.current_pages.forward(callback_from_id)
        case CallbackList.invoices_pagination_backward:
            InvoiceModule.current_pages.backward(callback_from_id)
        case _:
            return True

    new_keyboard = InvoiceModule.generate_keyboard(user_invoices, callback_from_id)

    text = query.message.text_html

    await ctx.update_message(
        text=text, message_id=query.message.message_id, reply=new_keyboard
    )

    return False


async def handle_invites_pagination_buttons(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """
    query = ctx.update.callback_query
    callback_from_id = query.from_user.id
    able_to_create_invite = (
        ctx.user.invite_limit - len(ctx.user.get_invites()) > 0
        if not ctx.user.has_invoice()
        else True
    )

    match query.data:
        case CallbackList.invites_pagination_forward:
            InviteModule.current_pages.forward(callback_from_id)
        case CallbackList.invites_pagination_backward:
            InviteModule.current_pages.backward(callback_from_id)
        case _:
            return True

    new_keyboard = InviteModule.generate_keyboard(
        ctx.user.get_display_invites(), callback_from_id, able_to_create_invite
    )

    text = query.message.text_html

    await ctx.update_message(
        text=text, message_id=query.message.message_id, reply=new_keyboard
    )

    return False


async def handle_common_callbacks(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """
    query = ctx.update.callback_query
    query_data = query.data
    callback_query_id = query.id

    match query_data:
        case CallbackList.available_subs_list:
            await available_subs(ctx)
            return False
        case CallbackList.my_subs_list:
            await my_subs(ctx)
            return False
        case CallbackList.profile:
            await handlers.menu_handler.profile_handler(ctx, True)
            return False
        case CallbackList.invoices:
            await invoices(ctx)
            return False
        case CallbackList.invites:
            await invites(ctx)
            return False
        case CallbackList.create_invite:
            await create_invite(ctx)
            return False
        case CallbackList.no_elements:
            await ctx.answer_callback(phrases.callback_no_elements, callback_query_id)
            return False
        case _:
            return True


async def available_subs(ctx: BotContext) -> bool:
    subs = ctx.user.get_subs(ListType.AVAILABLE_SUBS)
    keyboard = SubscriptionModule.generate_keyboard(
        subs, ctx.update.callback_query.from_user.id, ListType.AVAILABLE_SUBS
    )
    await ctx.update_message(
        text=phrases.main_menu_available_bot_answer,
        reply=keyboard,
        message_id=ctx.update.callback_query.message.message_id,
    )
    return False


async def my_subs(ctx: BotContext) -> bool:
    subs = ctx.user.get_subs(ListType.MY_SUBS)
    keyboard = SubscriptionModule.generate_keyboard(
        subs, ctx.update.callback_query.from_user.id, ListType.MY_SUBS
    )
    await ctx.update_message(
        text=phrases.main_menu_available_bot_answer,
        reply=keyboard,
        message_id=ctx.update.callback_query.message.message_id,
    )
    return False


async def invoices(ctx: BotContext) -> bool:
    invs = ctx.user.get_invoices()
    keyboard = InvoiceModule.generate_keyboard(
        invs, ctx.update.callback_query.from_user.id
    )
    await ctx.update_message(
        text="<b>🧾 счета</b>\n\nздесь ты можешь просмотреть свои счета 💳",
        reply=keyboard,
        message_id=ctx.update.callback_query.message.message_id,
    )
    return False


async def invites(ctx: BotContext) -> bool:
    display_invites = ctx.user.get_display_invites()
    available_invites = (
        ctx.user.invite_limit - len(display_invites)
        if not ctx.user.has_invoice()
        else 1
    )

    message = (
        "<b>🔗 инвайты</b>\n\nздесь ты можешь создавать инвайты, которые можешь подарить своему другу\n"
        "после перехода по ссылке твой друг получит полноценный доступ к боту\n\n"
        "{invited}\n\nу тебя доступно {invites_count} инвайтов"
    )

    users = [i for i in User.find().all() if i.referral and i.referral == ctx.user.id]

    invited_users = []
    for invited_user in users:
        try:
            user = await ctx.context.bot.get_chat(invited_user.id)
        except TelegramError:
            user = None

        if user and user.username:
            user_mention = f"@{user.username}"
        elif user and user.full_name:
            user_mention = f"{user.full_name}"
        else:
            user_mention = invited_user.name

        invited_users.append(user_mention)

    keyboard = InviteModule.generate_keyboard(
        display_invites, ctx.user.id, available_invites > 0
    )

    if not invited_users:
        message = message.replace("{invited}", "ты еще никого не приглашал 🐸")
    else:
        invited_phrase = "<b>ты пригласил:</b> " + str.join(", ", invited_users)
        message = message.replace("{invited}", invited_phrase)

    invites_count_phrase = (
        f"{available_invites} из {ctx.user.invite_limit}"
        if not ctx.user.has_invoice()
        else "неограниченное количество"
    )

    message = message.replace("{invites_count}", invites_count_phrase)

    await ctx.update_message(
        message, reply=keyboard, message_id=ctx.update.callback_query.message.message_id
    )
    return False


async def create_invite(ctx: BotContext) -> bool:
    if len(ctx.user.get_subs(ListType.MY_SUBS)) < 1:
        await ctx.answer_callback_popout(phrases.callback_at_least_one_sub)
        return False

    user_invites = ctx.user.get_invites()
    if (
        (ctx.user.invite_limit - len(user_invites)) <= 0
    ) and not ctx.user.has_invoice():
        await ctx.answer_callback(phrases.callback_no_invites)
        return False

    invite = Invite.create_invite(ctx.user.id)
    message = (
        f"<b>🔗 инвайт №{invite.id}</b>\n\n<b>приглашение:</b> <code>{invite.get_url()}</code>\n"
        f"<b>действительно до:</b> "
        f"{DateTimeUtils.day_and_month_in_words(invite.issue_date + datetime.timedelta(days=life_time_in_days))}"
    )

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton(phrases.go_back, callback_data=CallbackList.invites)]]
    )

    await ctx.update_message(message, reply=keyboard)
    invite.save()
