import datetime

import sentry_sdk
import telegram

from background_services.repeating_service import RepeatingService
from database_models.revolut_exchange_rate import RevolutExchangeRate
from enums.currency import Currency
from utils.currency_converter import CurrencyConverter


class RevolutService(RepeatingService):
    bot: telegram.Bot

    def __init__(self):
        now = datetime.datetime.now()
        super().__init__(
            12 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 10, 0, 0)
        )
        self.name = "RevolutService"

    def do_work(self):
        currencies = [Currency.TRY]

        for currency in currencies:
            try:
                rate = RevolutExchangeRate(
                    currency=str(currency),
                    exchange_rate=CurrencyConverter.get_rate_through_revolut(
                        currency, Currency.EUR
                    ),
                )
                rate.save()
            except Exception as e:
                sentry_sdk.capture_exception(e)
                continue
