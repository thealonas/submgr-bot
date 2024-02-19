import datetime
from typing import Optional, List

from redis_om import NotFoundError
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import phrases
import utils.keyboard_utils
from background_services.invoice_service import InvoiceService
from database_models.invoice import Invoice
from database_models.subscription import Subscription, ShiftType
from database_models.user import User
from enums.list_type import ListType
from enums.period import Period
from enums.subscription_type import SubscriptionType
from models.bot_context import BotContext
from models.pagination_dictionary import PaginationDictionary
from modules.pagination_module import PaginationModule
from notifiers.subscription_notifier import SubscriptionNotifier
from utils.callback_utils import ConfigurableCallbackList, CallbackList
from utils.datetime_utils import DateTimeUtils


class SubscriptionModuleOutput:
    message_text: str
    reply: Optional[InlineKeyboardMarkup]

    def __init__(self, message_text: str, reply: Optional[InlineKeyboardMarkup]):
        self.message_text = message_text
        self.reply = reply


class CurrentPagesStorage:
    available_subscription_storage: PaginationDictionary[int, int] = (
        PaginationDictionary()
    )
    my_subscription_storage: PaginationDictionary[int, int] = PaginationDictionary()


class SubscriptionModule:
    ITEMS_PER_PAGE = 4
    current_pages: CurrentPagesStorage = CurrentPagesStorage()

    # нужно чтобы два раза не вызывалось и чел не заходил по два раза в подписку
    joining_users: List[int] = []
    leaving_users: List[int] = []

    @staticmethod
    def __form_base_output() -> SubscriptionModuleOutput:
        output = SubscriptionModuleOutput("", None)
        return output

    @staticmethod
    def not_active() -> SubscriptionModuleOutput:
        return SubscriptionModuleOutput(
            message_text="эта подпсика недоступна 😿", reply=None
        )

    @staticmethod
    def generate_keyboard(
        subs: List[Subscription], user_id: int, list_type: ListType
    ) -> InlineKeyboardMarkup:
        if len(subs) == 0 or not subs:
            no_subs_keyboard = [
                [utils.keyboard_utils.no_elements_button],
            ]

            return InlineKeyboardMarkup(no_subs_keyboard)

        keyboard = []

        page = 0
        left_button_callback = ""
        right_button_callback = ""
        overview_callback = (
            ConfigurableCallbackList.my_sub_overview
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview
        )

        match list_type:
            case ListType.MY_SUBS:
                left_button_callback = CallbackList.my_subs_list_pagination_backward
                right_button_callback = CallbackList.my_subs_list_pagination_forward
                page = SubscriptionModule.current_pages.my_subscription_storage.get(
                    user_id, 0
                )

            case ListType.AVAILABLE_SUBS:
                left_button_callback = (
                    CallbackList.available_subs_list_pagination_backward
                )
                right_button_callback = (
                    CallbackList.available_subs_list_pagination_forward
                )
                page = (
                    SubscriptionModule.current_pages.available_subscription_storage.get(
                        user_id, 0
                    )
                )

        start_index = page * SubscriptionModule.ITEMS_PER_PAGE
        end_index = start_index + SubscriptionModule.ITEMS_PER_PAGE

        for i in range(start_index, end_index, 2):
            row = []
            for j in range(i, min(i + 2, len(subs))):
                sub = subs[j]
                button_text = sub.name
                callback_data = overview_callback.box_value(sub.id)
                row.append(
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                )
            keyboard.append(row)

        pagination = PaginationModule.get_pagination_buttons(
            subs, page, right_button_callback, left_button_callback, end_index
        )

        if pagination:
            keyboard.append(pagination)

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def handle_pagination_button_press(user_id: int, callback_data: str):
        match callback_data:
            case CallbackList.my_subs_list_pagination_backward:
                SubscriptionModule.current_pages.my_subscription_storage.backward(
                    user_id
                )

            case CallbackList.my_subs_list_pagination_forward:
                SubscriptionModule.current_pages.my_subscription_storage.forward(
                    user_id
                )

            case CallbackList.available_subs_list_pagination_backward:
                SubscriptionModule.current_pages.available_subscription_storage.backward(
                    user_id
                )

            case CallbackList.available_subs_list_pagination_forward:
                SubscriptionModule.current_pages.available_subscription_storage.forward(
                    user_id
                )

    @staticmethod
    async def overview(
        ctx: BotContext,
        sub: Subscription,
        user_in_subscription: bool,
        list_type: ListType,
    ):
        if not sub.is_active:
            await ctx.answer_callback(phrases.callback_query_invalid)
            return

        credentials = ConfigurableCallbackList.sub_credential.box_value(sub.id)

        # фокусы с клавиатурой
        match list_type:
            case ListType.MY_SUBS:
                desc = ConfigurableCallbackList.my_sub_overview_faq.box_value(sub.id)
                process = ConfigurableCallbackList.my_sub_overview_process.box_value(
                    sub.id
                )
                join = ConfigurableCallbackList.my_sub_overview_join.box_value(sub.id)
                leave = ConfigurableCallbackList.my_sub_overview_leave.box_value(sub.id)
                return_callback = CallbackList.my_subs_list

            case ListType.AVAILABLE_SUBS:
                desc = ConfigurableCallbackList.available_sub_overview_faq.box_value(
                    sub.id
                )
                process = (
                    ConfigurableCallbackList.available_sub_overview_process.box_value(
                        sub.id
                    )
                )
                join = ConfigurableCallbackList.available_sub_overview_join.box_value(
                    sub.id
                )
                leave = ConfigurableCallbackList.available_sub_overview_leave.box_value(
                    sub.id
                )
                return_callback = CallbackList.available_subs_list

            case _:
                raise ValueError(f"list_type is invalid: {list_type}")

        keyboard = []

        static_section = [
            InlineKeyboardButton(phrases.menu_sub_overview_faq, callback_data=desc),
            InlineKeyboardButton(
                phrases.menu_sub_overview_process, callback_data=process
            ),
        ]

        if user_in_subscription and sub.shared and sub.credentials:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        phrases.menu_sub_overview_credentials, callback_data=credentials
                    )
                ]
            )

        keyboard.append(static_section)

        if not user_in_subscription and not sub.is_full:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        phrases.menu_sub_overview_join, callback_data=join
                    )
                ]
            )
        elif user_in_subscription:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        phrases.menu_sub_overview_leave, callback_data=leave
                    )
                ]
            )

        keyboard.append(
            [InlineKeyboardButton(phrases.go_back, callback_data=return_callback)]
        )

        price = (
            # автоматический подсчет если подписка заполнена
            sub.price_in_eur
            if sub.is_full
            # если резерв - считаем цену на всех
            else (
                sub.calculate_price_in_eur(sub.billing.total_seats)
                if sub.reserve
                # если отображаем в доступных подписках - считаем цену если бы в нее еще кто-то зашел
                else (
                    sub.calculate_price_in_eur(len(sub.billing.members) + 1)
                    if list_type is ListType.AVAILABLE_SUBS
                    # во всех остальных случаях делим цену на всех участников
                    else sub.calculate_price_in_eur(len(sub.billing.members))
                )
            )
        )

        if sub.effective_type is SubscriptionType.group:
            message = (
                f"<b>{sub.name}</b>\n\n{sub.info.description}\n\n"
                f"<b>статус:</b> {'резервация' if sub.reserve else 'активная'}\n"
                f"<b>свободных мест:</b> {sub.free_slots}\n"
                f"<b>цена подписки:</b> €<code>{price:.2f}</code>\n"
            )
        else:
            message = (
                f"<b>{sub.name}</b>\n\n{sub.info.description}\n\n"
                f"<b>цена подписки:</b> €<code>{price:.2f}</code>\n"
            )

        if list_type is ListType.MY_SUBS and user_in_subscription:
            try:
                next_invoice_date = sub.payday(ctx.user.id)
                next_invoice = None
                if next_invoice_date:
                    next_invoice = (
                        DateTimeUtils.full_date_in_words(next_invoice_date)
                        if sub.billing.effective_period is Period.yearly
                        else DateTimeUtils.day_and_month_in_words(next_invoice_date)
                    )

                if (
                    not (sub.reserve and sub.free_slots > 0)
                    and sub.billing.next_invoice_date
                    and next_invoice
                ):
                    period = sub.paid_period(ShiftType.Paid, ctx.user.id)
                    message += f"<b>период:</b> {period}\n"
                    message += f"<b>следующий счёт:</b> {next_invoice}"
            except TypeError:
                pass

        await ctx.update_message(message, InlineKeyboardMarkup(keyboard))

    @staticmethod
    def __sub_info_base_output(
        sub: Subscription, list_type: ListType
    ) -> SubscriptionModuleOutput:
        if not sub.is_active:
            return SubscriptionModule.not_active()

        output = SubscriptionModule.__form_base_output()

        callback = (
            ConfigurableCallbackList.my_sub_overview.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview.box_value(sub.id)
        )
        keyboard = [[InlineKeyboardButton(phrases.go_back, callback_data=callback)]]

        output.reply = InlineKeyboardMarkup(keyboard)
        return output

    @staticmethod
    def process(sub: Subscription, list_type: ListType) -> SubscriptionModuleOutput:
        if not sub.is_active:
            return SubscriptionModule.not_active()

        output = SubscriptionModule.__sub_info_base_output(sub, list_type)
        output.message_text = f"<b>{sub.name}: процесс</b>\n\n{sub.info.process}"
        return output

    @staticmethod
    def faq(sub: Subscription, list_type: ListType) -> SubscriptionModuleOutput:
        if not sub.is_active:
            return SubscriptionModule.not_active()

        output = SubscriptionModule.__sub_info_base_output(sub, list_type)
        output.message_text = f"<b>{sub.name}: чаво</b>\n\n{sub.info.faq}"
        return output

    @staticmethod
    async def handle_join_confirm(
        ctx: BotContext, sub: Subscription, list_type: ListType
    ):
        if ctx.user.id in SubscriptionModule.joining_users:
            await ctx.answer_callback(phrases.callback_wait)
            return

        if not sub.is_active:
            await ctx.answer_callback("эта подписка недоступна ❌")
            return

        SubscriptionModule.joining_users.append(ctx.user.id)

        user = ctx.user

        callback = ctx.update.callback_query
        callback_id = callback.id

        callback_data = (
            ConfigurableCallbackList.my_sub_overview.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview.box_value(sub.id)
        )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(phrases.go_back, callback_data=callback_data)]]
        )

        if sub.is_full:
            await ctx.context.bot.answer_callback_query(
                callback_id, text=phrases.callback_sub_is_full
            )
            return

        message_id = ctx.update.callback_query.message.id
        conflict_sub = await SubscriptionModule.get_conflict_sub(ctx.user, sub.id)

        if conflict_sub is Subscription:
            await ctx.answer_callback_popout(
                f"❌ ты не можешь вступить в эту подписку, "
                f'так как ты подписан на "{conflict_sub.name}"'
            )
            return

        if conflict_sub is int and conflict_sub != 0:
            await ctx.answer_callback(f"❌ ты не можешь вступить в эту подписку")
            return

        if user.id in sub.billing.members:
            await ctx.answer_callback(phrases.callback_already_joined)
            return

        await ctx.update_message(
            text=f"<b>{sub.name}\n\n✅ ты успешно вступил в подписку</b>",
            reply=keyboard,
            message_id=message_id,
        )

        sub.billing.members.append(user.id)
        sub.save()

        user.set_joined_date(sub.id)

        if sub.effective_type is SubscriptionType.group:
            await SubscriptionNotifier.notify_member_joined(ctx, sub.id, user.id)
        else:
            InvoiceService.invoice_individual_sub_member(sub, user.id)

        SubscriptionModule.joining_users.remove(ctx.user.id)

    @staticmethod
    async def handle_leave_confirm(
        ctx: BotContext, sub: Subscription, list_type: ListType
    ):
        if ctx.user.id in SubscriptionModule.leaving_users:
            await ctx.answer_callback(phrases.callback_wait)
            return

        if not sub.is_active:
            return SubscriptionModule.not_active()

        SubscriptionModule.leaving_users.append(ctx.user.id)

        user = ctx.user

        invoices = Invoice.find((Invoice.user == user.id)).all()

        # те инвойсы которые не оплаченные и которые содержат подписку sub.id
        invoices = [
            i
            for i in invoices
            if not i.paid and sub.id in [b.sub_id for b in i.subscriptions]
        ]

        if invoices:
            for invoice in invoices:
                if not invoice.paid:
                    await ctx.answer_callback_popout(
                        "ты не можешь выйти из подписки с неоплаченным счетом 🤑"
                    )
                    SubscriptionModule.leaving_users.remove(ctx.user.id)
                    return

        if (sub.billing.next_invoice_date - datetime.date.today()).days <= 3:
            await ctx.answer_callback(
                "ты не можешь выйти из подпки за три дня до выставления счета 🤷‍♂️"
            )
            SubscriptionModule.leaving_users.remove(ctx.user.id)
            return

        if sub.billing.min_days:
            all_user_billings = [
                i for i in user.billing if i.sub_id == sub.id and i.joined
            ]
            if (
                all_user_billings
                and (datetime.date.today() - all_user_billings[0].joined).days
                < sub.billing.min_days
            ):
                await ctx.answer_callback(f"прошло слишком мало времени 🤷‍♂️")
                SubscriptionModule.leaving_users.remove(ctx.user.id)
                return

        callback_data = (
            ConfigurableCallbackList.my_sub_overview.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview.box_value(sub.id)
        )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(phrases.go_back, callback_data=callback_data)]]
        )

        if user.id not in sub.billing.members:
            await ctx.answer_callback(phrases.callback_already_left)

        await ctx.update_message(
            f"<b>{sub.name}\n\n✅ ты вышел из подписки</b>",
            reply=keyboard,
            message_id=ctx.update.callback_query.message.id,
        )

        sub.billing.members.remove(user.id)
        sub.save()

        user.set_joined_date(sub.id, None)

        if sub.effective_type is SubscriptionType.group:
            await SubscriptionNotifier.notify_member_left(ctx, sub.id, user.id)

        SubscriptionModule.leaving_users.remove(ctx.user.id)

    @staticmethod
    async def handle_join(ctx: BotContext, sub: Subscription, list_type: ListType):
        if not sub.is_active:
            return SubscriptionModule.not_active()

        user = ctx.user
        callback = ctx.update.callback_query
        callback_id = callback.id

        action_callback_data = (
            ConfigurableCallbackList.my_sub_overview_join_confirm.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview_join_confirm.box_value(
                sub.id
            )
        )

        back_button_callback_data = (
            ConfigurableCallbackList.my_sub_overview.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview.box_value(sub.id)
        )

        if sub.is_full:
            await ctx.context.bot.answer_callback_query(
                callback_id, text=phrases.callback_sub_is_full
            )
            return

        action_button = InlineKeyboardButton(
            "✅ да", callback_data=action_callback_data
        )

        back_button = InlineKeyboardButton(
            phrases.go_back, callback_data=back_button_callback_data
        )

        keyboard = InlineKeyboardMarkup(
            [
                [action_button],
                [back_button],
            ]
        )

        message_id = ctx.update.callback_query.message.id
        conflict_sub = await SubscriptionModule.get_conflict_sub(ctx.user, sub.id)

        if conflict_sub is Subscription:
            await ctx.answer_callback_popout(
                f"❌ ты не можешь вступить в эту подписку, "
                f'так как ты подписан на "{conflict_sub.name}"',
            )
            return

        if conflict_sub != 0:
            await ctx.answer_callback_popout(
                f"❌ ты не можешь вступить в эту подписку",
            )
            return

        if user.id in sub.billing.members:
            await ctx.answer_callback(phrases.callback_already_joined)

        datetime_func = (
            DateTimeUtils.full_date_in_words
            if sub.billing.effective_period is Period.yearly
            else DateTimeUtils.day_and_month_in_words
        )

        if sub.effective_type is SubscriptionType.individual:
            next_invoice = datetime_func(datetime.date.today())
        else:
            next_invoice = None

        if not next_invoice:
            text = f"<b>{sub.name}\n\nты точно хочешь вступить в эту подписку?</b>"
        else:
            text = f"<b>{sub.name}\n\nты точно хочешь вступить в эту подписку?</b>"
            f"\n\nтвой первый счёт придёт {next_invoice}. после его оплаты ты получишь доступ к подписке."

        await ctx.update_message(
            text=text,
            reply=keyboard,
            message_id=message_id,
        )

    @staticmethod
    async def handle_leave(ctx: BotContext, sub: Subscription, list_type: ListType):
        if not sub.is_active:
            await ctx.answer_callback("эта подписка недоступна ❌")
            return

        invoices: List[Invoice] = Invoice.find(Invoice.user == ctx.user.id).all()

        # те инвойсы которые не оплаченные и которые содержат подписку sub.id
        invoices = [
            i
            for i in invoices
            if not i.paid and sub.id in [b.sub_id for b in i.subscriptions]
        ]

        if invoices:
            for invoice in invoices:
                if not invoice.paid:
                    await ctx.answer_callback_popout(
                        "ты не можешь выйти из подписки с неоплаченным счетом 🤑"
                    )
                    return

        action_button_callback_data = (
            ConfigurableCallbackList.my_sub_overview_leave_confirm.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview_leave_confirm.box_value(
                sub.id
            )
        )

        back_button_callback_data = (
            ConfigurableCallbackList.my_sub_overview.box_value(sub.id)
            if list_type == ListType.MY_SUBS
            else ConfigurableCallbackList.available_sub_overview.box_value(sub.id)
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ да", callback_data=action_button_callback_data
                    )
                ],
                [
                    InlineKeyboardButton(
                        phrases.go_back, callback_data=back_button_callback_data
                    )
                ],
            ]
        )

        if ctx.user.id not in sub.billing.members:
            await ctx.answer_callback(phrases.callback_already_joined)

        await ctx.update_message(
            f"<b>{sub.name}\n\nты точно хочешь выйти из подписки?</b>",
            reply=keyboard,
            message_id=ctx.update.callback_query.message.id,
        )

    @staticmethod
    async def get_conflict_sub(user: User, sub_id: int) -> Subscription | int:
        """
        returns
        Subscription - found conflicted sub
        int other than 0 - conflict sub id if nothing found in db
        0 if nothing found
        """
        conflict_sub_id = user.can_join_forbidden_with(sub_id)

        if conflict_sub_id == 0:
            return 0

        try:
            conflict_sub = Subscription.get(conflict_sub_id)
        except NotFoundError:
            conflict_sub = None

        if not conflict_sub:
            return conflict_sub_id

        return conflict_sub

    @staticmethod
    async def password(ctx: BotContext, sub: Subscription):
        if not sub.is_active or not sub.credentials or not sub.shared:
            await ctx.answer_callback("эта подпсика недоступна 😿")
            return

        callback_data = ConfigurableCallbackList.my_sub_overview.box_value(sub.id)

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton(phrases.go_back, callback_data=callback_data)]]
        )

        await ctx.update_message(
            f"<b>{sub.name}: пароль</b>\n\n{sub.credentials}",
            reply=keyboard,
            message_id=ctx.update.callback_query.message.id,
        )
