from typing import Dict

from telegram import CallbackQuery

from database_models.subscription import Subscription
from enums.list_type import ListType
from models.bot_context import BotContext
from modules.subscription_module import SubscriptionModule
from utils.callback_utils import ConfigurableCallbackList, InlineCallback


class SubscriptionServiceInfo:
    sub: Subscription
    user: int
    in_sub: bool


class ConfigurableOutput:
    is_valid: bool
    callback: InlineCallback
    list_type: ListType
    data: str


async def handle_subscriptions_callback(
    ctx: BotContext, query: CallbackQuery, query_data: str, callback_from_id: int
) -> bool:
    """
    возвращает can_continue
    """

    data = get_configurable_output(query_data)

    if not data.is_valid:
        return True

    try:
        sub_info = get_sub_info(
            int(data.callback.extract_value(query_data)), callback_from_id
        )
    except ValueError:
        return True

    if data.callback is ConfigurableCallbackList.sub_credential:
        if not ctx.user.can_access_password_info(sub_info.sub.id):
            await ctx.answer_callback(
                "у тебя есть неоплаченный счёт, поэтому просмотр пароля недоступен 🙈"
            )
            return False

        await SubscriptionModule.password(ctx, sub_info.sub)
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview
        or data.callback is ConfigurableCallbackList.available_sub_overview
    ):
        await SubscriptionModule.overview(
            ctx, sub_info.sub, sub_info.in_sub, data.list_type
        )
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_process
        or data.callback is ConfigurableCallbackList.available_sub_overview_process
    ):
        data = SubscriptionModule.process(sub_info.sub, data.list_type)
        await ctx.update_message(
            text=data.message_text, reply=data.reply, message_id=query.message.id
        )
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_faq
        or data.callback is ConfigurableCallbackList.available_sub_overview_faq
    ):
        data = SubscriptionModule.faq(sub_info.sub, data.list_type)
        await ctx.update_message(
            text=data.message_text, reply=data.reply, message_id=query.message.id
        )
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_join_confirm
        or data.callback is ConfigurableCallbackList.available_sub_overview_join_confirm
    ):
        await SubscriptionModule.handle_join_confirm(ctx, sub_info.sub, data.list_type)
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_join
        or data.callback is ConfigurableCallbackList.available_sub_overview_join
    ):
        await SubscriptionModule.handle_join(ctx, sub_info.sub, data.list_type)
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_leave_confirm
        or data.callback
        is ConfigurableCallbackList.available_sub_overview_leave_confirm
    ):
        await SubscriptionModule.handle_leave_confirm(ctx, sub_info.sub, data.list_type)
        return False

    if (
        data.callback is ConfigurableCallbackList.my_sub_overview_leave
        or data.callback is ConfigurableCallbackList.available_sub_overview_leave
    ):
        await SubscriptionModule.handle_leave(ctx, sub_info.sub, data.list_type)
        return False

    return True


def get_configurable_output(callback_query: str) -> ConfigurableOutput:
    callbacks: Dict[InlineCallback, ListType] = {
        ConfigurableCallbackList.my_sub_overview_faq: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview_process: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview_join: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview_join_confirm: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview_leave: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview_leave_confirm: ListType.MY_SUBS,
        ConfigurableCallbackList.my_sub_overview: ListType.MY_SUBS,
        ConfigurableCallbackList.available_sub_overview_faq: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview_process: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview_join: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview_join_confirm: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview_leave: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview_leave_confirm: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.available_sub_overview: ListType.AVAILABLE_SUBS,
        ConfigurableCallbackList.sub_credential: ListType.MY_SUBS,
    }

    output = ConfigurableOutput()
    output.is_valid = False

    for callback in callbacks:
        list_type = callbacks[callback]

        if not callback.matches(callback_query):
            continue

        output.callback = callback
        output.is_valid = True
        output.data = callback.extract_value(callback_query)
        output.list_type = list_type
        return output

    return output


def get_sub_info(sub_id: int, user_id: int) -> SubscriptionServiceInfo:
    sub_info = SubscriptionServiceInfo()
    sub_query = Subscription.find(Subscription.id == sub_id).all()

    if not sub_query:
        raise RuntimeError(f"cannot find sub {sub_id}")

    sub_info.sub = sub_query[0]
    sub_info.in_sub = user_id in sub_info.sub.billing.members
    return sub_info
