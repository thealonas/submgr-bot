import random
import string
from datetime import date
from typing import List

import redis_om

from database_models.base_model import BaseModel, BaseEmbeddedModel


class InvoiceSubscriptionInfo(BaseEmbeddedModel):
    sub_id: int
    period_start_date: date
    period_end_date: date
    price: float

    class Meta:
        embedded = True


class Invoice(BaseModel):
    invoice_id: str = redis_om.Field(index=True, primary_key=True)
    user: int = redis_om.Field(index=True)
    date: date
    pay_till: date
    subscriptions: List[InvoiceSubscriptionInfo]
    paid: bool

    @staticmethod
    def generate_invoice_id():
        potential_id = 0
        found = True

        while found:
            potential_id = Invoice.__get_random_id()
            invoices = Invoice.find(Invoice.invoice_id == potential_id).all()

            if not invoices:
                found = False

        return potential_id

    @property
    def total_price(self) -> float:
        price = 0.0
        for sub in self.subscriptions:
            price += sub.price
        return price

    def has_subscription(self, sub_id: int) -> bool:
        for sub in self.subscriptions:
            if sub.sub_id == sub_id:
                return True
        return False

    @staticmethod
    def __get_random_id() -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

    class Meta:
        model_key_prefix = "invoice"
