import redis_om

from database_models.base_model import BaseModel
from enums.currency import Currency


class RevolutExchangeRate(BaseModel):
    currency: str = redis_om.Field(index=True, primary_key=True)
    exchange_rate: float

    @property
    def effective_currency(self) -> Currency:
        return Currency.from_str(self.currency)

    class Meta:
        model_key_prefix = "revolut"
