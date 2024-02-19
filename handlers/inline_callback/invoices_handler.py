from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import phrases
from background_services.reminder_service import ReminderService
from database_models.invoice import Invoice
from models.bot_context import BotContext
from modules.invoice_module import InvoiceModule
from utils.callback_utils import ConfigurableCallbackList, CallbackList
from utils.datetime_utils import DateTimeUtils


class InvoiceOutput:
    invoice: Invoice

    def __init__(self, invoice: Invoice):
        self.invoice = invoice


async def handle_invoices_callback(ctx: BotContext, query_data: str) -> bool:
    """
    возвращает can_continue
    """

    if ConfigurableCallbackList.invoice_overview.matches(query_data):
        return await invoice_overview(
            ctx, ConfigurableCallbackList.invoice_overview.extract_value(query_data)
        )

    if ConfigurableCallbackList.invoice_overview_notify.matches(query_data):
        return await ReminderService.remind_invoice(
            ctx,
            ConfigurableCallbackList.invoice_overview_notify.extract_value(query_data),
            True,
        )

    if ConfigurableCallbackList.invoice_pay.matches(query_data):
        return await invoice_pay(
            ctx, ConfigurableCallbackList.invoice_pay.extract_value(query_data), False
        )

    if ConfigurableCallbackList.invoice_pay_notify.matches(query_data):
        return await invoice_pay(
            ctx,
            ConfigurableCallbackList.invoice_pay_notify.extract_value(query_data),
            True,
        )

    if ConfigurableCallbackList.invoice_pay_confirm.matches(query_data):
        return await invoice_pay_confirm(
            ctx,
            ConfigurableCallbackList.invoice_pay_confirm.extract_value(query_data),
            False,
        )

    if ConfigurableCallbackList.invoice_pay_confirm_notify.matches(query_data):
        return await invoice_pay_confirm(
            ctx,
            ConfigurableCallbackList.invoice_pay_confirm_notify.extract_value(
                query_data
            ),
            True,
        )

    return True


def base_output(invoice_id: str) -> InvoiceOutput:
    invoices = Invoice.find(Invoice.invoice_id == invoice_id).all()
    if not invoices:
        raise ValueError("invoice not found")
    invoice = invoices[0]
    return InvoiceOutput(invoice)


async def invoice_overview(ctx: BotContext, invoice_id: str) -> bool:
    """
    вовзращает can_continue
    """

    try:
        output = base_output(invoice_id)
    except ValueError:
        await ctx.answer_callback("этого счёта больше нет 🤷‍♀️")
        return False

    invoice = output.invoice

    message = f"<b>🧾 счёт №{invoice.invoice_id}</b>\n\n"

    price = f"€<code>{invoice.total_price:.2f}</code>"

    sub_phrase = "\n".join(
        [InvoiceModule.generate_sub_phrase(i) for i in invoice.subscriptions]
    )

    message += f"<b>подписки</b>:\n{sub_phrase}\n"
    message += f"<b>цена</b>: {price}\n"
    message += (
        f"<b>счёт выставлен</b>: {DateTimeUtils.day_and_month_in_words(invoice.date)}\n"
    )
    message += f"<b>оплатить до</b>: {DateTimeUtils.day_and_month_in_words(invoice.pay_till)}\n\n"

    message += f"<b>статус</b>: {'✅ оплачен' if invoice.paid else '❌ не оплачен'}\n"

    keyboard = []

    if not invoice.paid:
        keyboard.append(
            [
                InlineKeyboardButton(
                    "💅 оплатить",
                    callback_data=ConfigurableCallbackList.invoice_pay.box_value(
                        invoice.invoice_id
                    ),
                )
            ]
        )
    keyboard.append(
        [InlineKeyboardButton(phrases.go_back, callback_data=CallbackList.invoices)]
    )

    keyboard = InlineKeyboardMarkup(keyboard)

    await ctx.update_message(
        message, keyboard, message_id=ctx.update.callback_query.inline_message_id
    )
    return False


async def invoice_pay(ctx: BotContext, invoice_id: str, notify: bool) -> bool:
    """
    вовзращает can_continue
    """
    try:
        output = base_output(invoice_id)
    except ValueError:
        await ctx.answer_callback("этого счёта больше нет 🤷‍♀️")
        return False

    invoice = output.invoice

    if invoice.paid:
        await ctx.answer_callback("этот счёт уже оплачен 🤷‍♀️")
        return False

    message = f"<b>💳 счёт №{invoice.invoice_id}</b>\n\n"
    message += f"получатель: <code>RED</code>\n"
    message += f"счёт: <code>RED</code>\n"
    message += f"BIC: <code>RED</code>\n"
    message += f"сумма: €<code>{invoice.total_price:.2f}</code>\n"

    groups = ", ".join([str(i.sub_id) for i in invoice.subscriptions])

    message += f"примечание: <code>group-id: {groups}</code>\n\n"
    message += f'<a href="https://revolut.me/RED/eur{invoice.total_price:.2f}/group-id: {groups}">оплатить банковской картой</a>\n'

    pay_button_callback = (
        ConfigurableCallbackList.invoice_pay_confirm_notify
        if notify
        else ConfigurableCallbackList.invoice_pay_confirm
    )

    back_button_callback = (
        ConfigurableCallbackList.invoice_overview_notify
        if notify
        else ConfigurableCallbackList.invoice_overview
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "💅 я оплатил", callback_data=pay_button_callback.box_value(invoice_id)
            )
        ],
        [
            InlineKeyboardButton(
                phrases.go_back,
                callback_data=back_button_callback.box_value(invoice_id),
            )
        ],
    ]

    keyboard = InlineKeyboardMarkup(keyboard)
    await ctx.update_message(
        message, keyboard, message_id=ctx.update.callback_query.inline_message_id
    )


async def invoice_pay_confirm(ctx: BotContext, invoice_id: str, notify: bool) -> bool:
    """
    вовзращает can_continue
    """
    try:
        output = base_output(invoice_id)
    except ValueError:
        await ctx.answer_callback("этого счёта больше нет 🤷‍♀️")
        return False

    invoice = output.invoice

    if invoice.paid:
        await ctx.answer_callback("этот счёт уже оплачен 🤷‍♀️")
    else:
        message = "спасибо за оплату, счёт теперь в обработке 🤗"
        await ctx.answer_callback_popout(message)
    if notify:
        await ReminderService.remind_invoice(ctx, invoice_id, update_message=True)
    else:
        await invoice_overview(ctx, invoice_id)
    return False
