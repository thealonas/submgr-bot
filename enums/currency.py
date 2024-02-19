from enum import Enum


class Currency(Enum):
    EUR = 0
    TRY = 1

    @staticmethod
    def from_str(currency: str) -> "Currency":
        if currency == "EUR":
            return Currency.EUR
        elif currency == "TRY":
            return Currency.TRY
        else:
            raise ValueError(f"Invalid currency: {currency}")

    def __str__(self) -> str:
        match self:
            case Currency.EUR:
                return "EUR"
            case Currency.TRY:
                return "TRY"
