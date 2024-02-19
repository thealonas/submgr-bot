from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import TelegramError

import phrases
from enums.list_type import ListType
from models.bot_context import BotContext
from modules.subscription_module import SubscriptionModule
from utils.callback_utils import CallbackList


async def menu_handler(ctx: BotContext) -> bool:
    """
    return bool is can_continue
    """

    if not ctx.update.message or not ctx.update.message.text:
        return True

    match ctx.update.message.text:
        case phrases.main_menu_available:
            await available_handler(ctx)
            return False

        case phrases.main_menu_active:
            await active_handler(ctx)
            return False

        case phrases.main_menu_profile:
            await profile_handler(ctx, False)
            return False

    return True


async def available_handler(ctx: BotContext):
    user_id = ctx.update.effective_user.id
    subs = ctx.user.get_subs(ListType.AVAILABLE_SUBS)
    keyboard = SubscriptionModule.generate_keyboard(
        subs, user_id, ListType.AVAILABLE_SUBS
    )
    await ctx.send_message(phrases.main_menu_available_bot_answer, reply=keyboard)


async def active_handler(ctx: BotContext):
    user_id = ctx.update.effective_user.id
    subs = ctx.user.get_subs(ListType.MY_SUBS)
    keyboard = SubscriptionModule.generate_keyboard(subs, user_id, ListType.MY_SUBS)
    await ctx.send_message(phrases.main_menu_active_bot_answer, reply=keyboard)


async def profile_handler(ctx: BotContext, delete_message: bool):
    subs = ctx.user.get_subs(ListType.MY_SUBS)

    keyboard = [
        [
            InlineKeyboardButton(text="🧾 счета", callback_data=CallbackList.invoices),
            InlineKeyboardButton(text="🔗 инвайты", callback_data=CallbackList.invites),
        ],
    ]

    internal_ids: dict[int, str] = {}

    for sub in subs:
        for bill in ctx.user.billing:
            if bill.sub_id != sub.id:
                continue
            if not bill.internal_id:
                continue
            internal_ids[bill.sub_id] = bill.internal_id

    if subs:
        subs_phrase = "\n"

        for sub in subs:
            if sub.id in internal_ids:
                subs_phrase += f"- {sub.name} ({internal_ids[sub.id]})\n"
            else:
                subs_phrase += f"- {sub.name}\n"
    else:
        subs_phrase = "❌\n"

    profile = ""

    profile += "<b>👨‍🦱 профиль</b>\n\n"
    profile += f"<b>имя:</b> {ctx.user.name}\n"

    if ctx.user.email:
        profile += f"<b>почта:</b> <code>{ctx.user.email}</code>\n"

    profile += f"<b>активные подписки:</b> {subs_phrase}"

    referral = ctx.user.referral

    if referral:
        try:
            user = await ctx.context.bot.get_chat(referral)
        except TelegramError:
            user = None

        if user and user.username:
            user_mention = f"@{user.username}"
        elif user and user.full_name:
            user_mention = f"{user.full_name}"
        else:
            user_mention = None

        if user_mention:
            profile += f"<b>тебя пригласил:</b> {user_mention}\n"

    if ctx.user.banned:
        profile += f"<b>заблокирован: {ctx.user.ban_reason}</b>\n"

    if delete_message:
        await ctx.update_message(profile, reply=InlineKeyboardMarkup(keyboard))
    else:
        await ctx.send_message(profile, reply=InlineKeyboardMarkup(keyboard))
