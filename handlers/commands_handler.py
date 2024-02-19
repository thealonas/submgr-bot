import sentry_sdk
from telegram import Chat
from telegram.error import TelegramError

from database_models.subscription import Subscription
from database_models.user import User
from models.bot_context import BotContext


async def get_chat(ctx: BotContext, chat_id: str | int) -> Chat | None:
    try:
        return await ctx.context.bot.get_chat(chat_id)
    except TelegramError:
        return None


async def commands_handler(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """

    if (
        not ctx.update.message
        or not ctx.update.message.text_markdown_v2
        or not ctx.user.admin
    ):
        return True

    command, *args = ctx.update.message.text_html.split()

    async def try_commands(context: BotContext, com: str, arg_list) -> bool:
        if com == "/send":
            if len(arg_list) < 2:
                await context.send_message(
                    "❌ недостаточно аргументов для команды /send"
                )
                return False
            return await handle_subscriptions(
                context,
                int(arg_list[0]),
                ctx.update.message.text_html.replace(com, "")
                .replace(arg_list[0], "")
                .strip(),
            )
        elif com == "/send_user":
            if len(arg_list) < 2:
                await context.send_message(
                    "❌ недостаточно аргументов для команды /send_user"
                )
                return False
            return await handle_user(
                context,
                arg_list[0],
                ctx.update.message.text_html.replace(com, "")
                .replace(arg_list[0], "")
                .strip(),
            )
        elif com == "/send_all":
            if len(arg_list) < 1:
                await context.send_message(
                    "❌ недостаточно аргументов для команды /send_all"
                )
                return False
            return await handle_all_users(
                context, ctx.update.message.text_html.replace(com, "").strip()
            )
        else:
            return True

    try:
        return await try_commands(ctx, command, args)
    except Exception as e:
        await ctx.send_message(f"невозможно выполнить операцию: {e}")
        sentry_sdk.capture_exception(e)
        return False


async def handle_subscriptions(
    ctx: BotContext, sub_id: int, markdown_text: str
) -> bool:
    subs = Subscription.find(Subscription.id == sub_id).all()
    if not subs:
        await ctx.send_message(f"подписка {sub_id} не найдена 🪡")
        return False

    sub: Subscription = subs[0]

    if not sub.billing.members:
        await ctx.send_message("в этой подписке нет участников 🙆‍♀️")
        return False

    for member in sub.billing.members:
        try:
            await ctx.send_message(markdown_text, chat_id=member)
        except Exception as e:
            await ctx.send_message(f"не удалось отправить сообщение {member}: {e}")
            sentry_sdk.capture_exception(e)
            continue

    await ctx.send_message("готово ✅")


async def handle_user(ctx: BotContext, user: str, markdown_text: str) -> bool:
    chat = await get_chat(ctx, user)
    if not chat:
        await ctx.send_message(f"пользователь {user} не найден 🪡")
        return False

    users = User.find(User.id == chat.id).all()
    if not users:
        await ctx.send_message(f"пользователь {user} не найден 🪡")
        return False

    try:
        await ctx.send_message(markdown_text, chat_id=chat.id)
    except Exception as e:
        await ctx.send_message(
            f"не удалось отправить сообщение "
            f"{f'@{chat.username}' if chat.username else f'{chat.full_name}'}: {e}"
        )
        sentry_sdk.capture_exception(e)
        return False

    await ctx.send_message("готово ✅")


async def handle_all_users(ctx: BotContext, markdown_text: str) -> bool:
    users = User.find().all()

    succeed_users = []
    failed_users = []

    for user in users:
        chat = await get_chat(ctx, user.id)

        user_log = f"- {user.id} ({user.name})"

        if not chat:
            failed_users.append(user_log)
            continue
        await ctx.send_message(markdown_text, chat_id=chat.id)
        succeed_users.append(user_log)

    message = "готово ✅\n\n"

    if failed_users:
        log = "\n".join(failed_users)
        message += f"❌ не удалось отправить сообщения:\n{log}\n\n"

    if succeed_users:
        log = "\n".join(succeed_users)
        message += f"✅ сообщение успешно отправлено:\n{log}\n\n"
    else:
        message += "сообщение никому отправлено не было"

    await ctx.send_message(message)

    return False
