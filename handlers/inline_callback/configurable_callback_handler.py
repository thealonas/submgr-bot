from handlers.inline_callback.invites_handler import handle_invites_callback
from handlers.inline_callback.invoices_handler import handle_invoices_callback
from handlers.inline_callback.subscriptions_handler import handle_subscriptions_callback
from models.bot_context import BotContext


async def handle_configurable_callback(ctx: BotContext) -> bool:
    """
    возвращает can_continue
    """

    query = ctx.update.callback_query
    query_data = query.data
    callback_from_id = query.from_user.id

    if not await handle_subscriptions_callback(
        ctx, query, query_data, callback_from_id
    ):
        return False

    if not await handle_invoices_callback(ctx, query_data):
        return False

    if not await handle_invites_callback(ctx, query_data):
        return False

    return True
