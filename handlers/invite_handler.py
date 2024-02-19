import re

import phrases
from database_models.user import User
from models.bot_context import BotContext
from utils import invite_utils, keyboard_utils


async def register_user(ctx: BotContext) -> bool:
    """
    return bool is can_continue
    """
    text = ctx.update.effective_message.text.replace("/start", "").strip()
    invite = invite_utils.try_find_invite(text)
    if invite is not None and not invite.used and not invite.spoiled:
        invite.use_invite(ctx.update.effective_user.id)
        User.create_default(ctx.update.effective_user, invite.from_user)
        await ctx.send_message(
            chat_id=ctx.update.effective_chat.id,
            text="привет! 👋\n\nдобро пожаловать в наш уютный бот по управлению групповыми подписками!🎉\n\n"
            "мы помогаем экономить тебе на групповых подписках, разделяя стоимость подписок между "
            "пользователями бота 🤝✨",
            reply=keyboard_utils.main_menu_keyboard(),
        )
        return False

    await ctx.send_message(
        chat_id=ctx.update.effective_chat.id, text=phrases.invalid_invite
    )
    return False


async def invite_handler(ctx: BotContext) -> bool:
    """
    return bool is can_continue
    """
    if ctx.user is not None:
        return True

    text = ctx.update.effective_message.text

    if text and re.compile(r"/start [A-Za-z0-9]+", re.IGNORECASE).match(text):
        return await register_user(ctx)

    await ctx.send_message(
        chat_id=ctx.update.effective_chat.id, text=phrases.you_are_not_invited
    )
    return False
