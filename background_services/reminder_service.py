import datetime
from enum import Enum

import sentry_sdk
import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.constants import ParseMode

from background_services.repeating_service import RepeatingService
from database_models.invoice import Invoice
from models.bot_context import BotContext
from modules.invoice_module import InvoiceModule
from utils.callback_utils import ConfigurableCallbackList
from utils.datetime_utils import DateTimeUtils


class DelayType(Enum):
    TwoDaysBefore = (0,)
    PayDay = (1,)
    TwoDaysPast = 2


class ReminderService(RepeatingService):
    bot: telegram.Bot

    TWO_DAYS_BEFORE = (
        "<b>💸 напоминаю про оплату (№{INVOICE})</b>\n\n<b>подписки:</b>\n{SUB}\n"
        "<b>цена:</b> €<code>{SUM}</code>\n<b>оплатить до:</b> {PAY_TILL}"
    )

    PAY_DAY = (
        "привет! 👋\n\nкажется, ты забыл оплатить счёт №{INVOICE} ☹️\n\n"
        "пожалуйста, оплати его в течении двух дней, иначе мы будем вынуждены отключить твою подписку "
        "и заблокировать доступ к боту 💣\n\nесли ты думаешь, что получил это сообщение по ошибке, "
        "свяжись с @likhner как можно скорее 📩"
    )

    TWO_DAYS_PAST = (
        "привет! 👋\n\nс грустью сообщаем, что из-за задолженностей по оплате подписок, "
        "мы вынуждены отключить твой доступ ко всем нашим сервисам 😞\n\nнам очень жаль, но к сожалению, "
        "доступ восстановить без оплаты задолженности и штрафа невозможно 💔\n\nесли ты считаешь, "
        "что это произошло по ошибке, пожалуйста, свяжись с @likhner как можно скорее, "
        "чтобы разобраться в ситуации 📩"
    )

    def __init__(self, bot: Bot):
        now = datetime.datetime.now()
        super().__init__(
            24 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 12, 0, 0)
        )
        self.name = "ReminderService"
        self.bot = bot

    async def do_work_async(self):
        invoices = [i for i in Invoice.find().all() if not i.paid]
        if not invoices:
            return

        for invoice in invoices:
            try:
                if invoice.pay_till == datetime.date.today():
                    await ReminderService.send_reminder(
                        self.bot, invoice, DelayType.PayDay
                    )
                elif invoice.pay_till == datetime.date.today() - datetime.timedelta(
                    days=2
                ):
                    await ReminderService.send_reminder(
                        self.bot, invoice, DelayType.TwoDaysPast
                    )
                elif invoice.pay_till == datetime.date.today() + datetime.timedelta(
                    days=2
                ):
                    await ReminderService.send_reminder(
                        self.bot, invoice, DelayType.TwoDaysBefore
                    )
                else:
                    continue
            except Exception as e:
                sentry_sdk.capture_exception(e)
                continue

    @staticmethod
    async def remind_invoice(
        ctx: BotContext, invoice_id: str, update_message: bool
    ) -> bool:
        invoices = Invoice.find(Invoice.invoice_id == invoice_id).all()
        if not invoices:
            return False

        invoice = invoices[0]

        if invoice.pay_till == datetime.date.today():
            await ReminderService.send_reminder(
                None, invoice, DelayType.PayDay, ctx, update_message
            )
        elif invoice.pay_till == datetime.date.today() - datetime.timedelta(days=2):
            await ReminderService.send_reminder(
                None, invoice, DelayType.TwoDaysPast, ctx, update_message
            )
        elif invoice.pay_till == datetime.date.today() + datetime.timedelta(days=2):
            await ReminderService.send_reminder(
                None, invoice, DelayType.TwoDaysBefore, ctx, update_message
            )

        return False

    @staticmethod
    async def send_reminder(
        bot: Bot | None,
        invoice: Invoice,
        delay_type: DelayType,
        ctx: BotContext | None = None,
        update_message: bool = False,
    ):
        invoice_phrase = invoice.invoice_id
        sub_phrase = "\n".join(
            [InvoiceModule.generate_sub_phrase(i) for i in invoice.subscriptions]
        )
        pay_till_phrase = DateTimeUtils.day_and_month_in_words(invoice.pay_till)
        sum_phrase = f"{invoice.total_price:.2f}"

        match delay_type:
            case DelayType.TwoDaysBefore:
                message = ReminderService.TWO_DAYS_BEFORE
                can_pay = True
            case DelayType.PayDay:
                message = ReminderService.PAY_DAY
                can_pay = True
            case DelayType.TwoDaysPast:
                message = ReminderService.TWO_DAYS_PAST
                can_pay = False
            case _:
                raise RuntimeError(f"Unknown delay type {delay_type}")

        message = (
            message.replace("{INVOICE}", invoice_phrase)
            .replace("{SUB}", sub_phrase)
            .replace("{PAY_TILL}", pay_till_phrase)
            .replace("{SUM}", sum_phrase)
        )

        keyboard = (
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "📪 оплатить",
                            callback_data=ConfigurableCallbackList.invoice_pay_notify.box_value(
                                invoice.invoice_id
                            ),
                        )
                    ]
                ]
            )
            if can_pay
            else None
        )

        try:
            if not update_message or not ctx:
                await bot.send_message(
                    invoice.user,
                    message,
                    parse_mode=ParseMode.HTML,
                    reply_markup=keyboard,
                    disable_web_page_preview=True,
                )
            else:
                await ctx.update_message(message, reply=keyboard)
        except Exception as e:
            sentry_sdk.capture_exception(e)
