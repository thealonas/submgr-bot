from typing import List

from redis import RedisError
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import phrases
from database_models.invoice import Invoice, InvoiceSubscriptionInfo
from database_models.subscription import Subscription
from enums.period import Period
from models.pagination_dictionary import PaginationDictionary
from modules.pagination_module import PaginationModule
from utils import keyboard_utils
from utils.callback_utils import ConfigurableCallbackList, CallbackList
from utils.datetime_utils import DateTimeUtils


class InvoiceModule:
    ITEMS_PER_PAGE = 4

    current_pages: PaginationDictionary[int, int] = PaginationDictionary()

    @staticmethod
    def generate_keyboard(
        invoices: List[Invoice], user_id: int
    ) -> InlineKeyboardMarkup:
        back_button = InlineKeyboardButton(
            phrases.go_back, callback_data=CallbackList.profile
        )

        if len(invoices) == 0 or not invoices:
            return InlineKeyboardMarkup(
                [[keyboard_utils.no_elements_button], [back_button]]
            )

        keyboard = []

        # Сортировка по ID подписки
        invoices = sorted(invoices, key=lambda x: x.date, reverse=True)

        left_button_callback = CallbackList.invoices_pagination_backward
        right_button_callback = CallbackList.invoices_pagination_forward
        overview_callback = ConfigurableCallbackList.invoice_overview

        page = InvoiceModule.current_pages.get(user_id, 0)

        start_index = page * InvoiceModule.ITEMS_PER_PAGE
        end_index = start_index + InvoiceModule.ITEMS_PER_PAGE

        for i in range(start_index, end_index, 2):
            row = []
            for j in range(i, min(i + 2, len(invoices))):
                invoice = invoices[j]
                try:
                    first_sub = (
                        Subscription.find(
                            Subscription.id == invoice.subscriptions[0].sub_id
                        )
                        .all()[0]
                        .name
                    )
                    sub_name = f" — {first_sub}"
                    if len(invoice.subscriptions) > 1:
                        sub_name += f" + {len(invoice.subscriptions) - 1}"
                except (RedisError, IndexError):
                    sub_name = ""
                button_text = f"🧾 {invoice.invoice_id}{sub_name}"
                callback_data = overview_callback.box_value(invoice.invoice_id)
                row.append(
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                )
            keyboard.append(row)

        pagination = PaginationModule.get_pagination_buttons(
            invoices, page, right_button_callback, left_button_callback, end_index
        )

        if pagination:
            keyboard.append(pagination)

        keyboard.append([back_button])

        return InlineKeyboardMarkup(keyboard)

    @staticmethod
    def generate_sub_phrase(sub_info: InvoiceSubscriptionInfo) -> str:
        sub: Subscription = Subscription.find(Subscription.id == sub_info.sub_id)[0]

        if sub.billing.effective_period is Period.monthly:
            date_to_string_method = DateTimeUtils.day_and_month_in_words
        else:
            date_to_string_method = DateTimeUtils.full_date_in_words

        date_phrase = (
            f"{date_to_string_method(sub_info.period_start_date)} – "
            f"{date_to_string_method(sub_info.period_end_date)}"
        )

        price_phrase = f"€<code>{sub_info.price:.2f}</code>"

        return f"- {sub.name} ({date_phrase}) – {price_phrase}"
