import requests

from database_models.revolut_exchange_rate import RevolutExchangeRate
from enums.currency import Currency


class CurrencyConverter:
    URL_TEMPLATE = (
        "https://www.revolut.com/api/exchange/quote?amount={AMOUNT}"
        "&country=LV&fromCurrency={FROM}&isRecipientAmount=false&toCurrency={TO}"
    )

    @staticmethod
    def get_rate_through_revolut(
        from_currency: Currency, to_currency: Currency
    ) -> float:
        if from_currency == to_currency:
            raise ValueError("Currencies are the same")

        url = (
            CurrencyConverter.URL_TEMPLATE.replace("{AMOUNT}", str(int(1 * 100)))
            .replace("{FROM}", from_currency.name)
            .replace("{TO}", to_currency.name)
        )

        response = requests.get(url, headers={"Accept-Language": "en"})
        content = response.json()
        rate = content.get("rate", {}).get("rate")

        if rate is None:
            raise ValueError("Invalid response")

        return float(rate)

    @staticmethod
    def convert_to_eur(amount: float, from_currency: Currency) -> float:
        if from_currency == Currency.EUR:
            return amount

        rates = RevolutExchangeRate.find().all()
        for rate in rates:
            if rate.effective_currency == from_currency:
                return amount * rate.exchange_rate

        raise RuntimeError("No currency was found in db")
