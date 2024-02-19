import phrases
from handlers.typing.typing_storage import TypingStorage, TypingStage
from models.bot_context import BotContext

typing_storage: TypingStorage[int, TypingStage] = TypingStorage()


async def typing_handler(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """
    if not ctx.user or (ctx.user.id not in typing_storage):
        return True

    match typing_storage[ctx.user.id]:
        case _:
            await ctx.send_message(phrases.callback_query_invalid)
            raise ValueError(f"invalid typing stage ({typing_storage[ctx.user.id]})")
