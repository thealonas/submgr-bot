import datetime
from datetime import date
from enum import Enum
from typing import List, Optional

import redis_om

from database_models.base_model import BaseModel, BaseEmbeddedModel
from enums.currency import Currency
from enums.period import Period
from enums.subscription_type import SubscriptionType
from utils.currency_converter import CurrencyConverter
from utils.datetime_utils import DateTimeUtils


class Billing(BaseEmbeddedModel):
    min_days: Optional[int]
    price: float
    currency: str
    period: str
    next_invoice_date: Optional[date]
    total_seats: Optional[int]
    members: List[int]

    @property
    def effective_currency(self) -> Currency:
        return Currency.from_str(self.currency)

    @property
    def effective_period(self) -> Period:
        return Period.from_str(self.period)

    class Meta:
        embedded = True


class Info(BaseEmbeddedModel):
    description: str
    faq: str
    process: str

    class Meta:
        embedded = True


class ShiftType(Enum):
    """
    shift:
    0 - уже оплачено ( с payday - 1 по payday)
    1 - будет оплачено (c payday по payday + 1)
    """

    Paid = (0,)
    WillBePaid = 1


class Subscription(BaseModel):
    id: int = redis_om.Field(index=True, primary_key=True)
    is_active: bool
    reserve: bool
    name: str
    type: str
    shared: bool
    credentials: Optional[str]
    forbidden_with: Optional[List[int]]
    billing: Billing
    info: Info

    @property
    def is_full(self) -> bool:
        return self.billing.total_seats == len(self.billing.members)

    def payday(self, user_id: Optional[int] = None) -> date:
        from database_models.user import User

        if self.effective_type is SubscriptionType.individual:
            if not user_id:
                raise ValueError("User is required for individual subscriptions")

            user: User = User.find(User.id == user_id).all()[0]
            billing_date = user.get_sub_period(self.id)

            if billing_date < date.today():
                user.set_sub_period(self.id, date.today())
                return date.today()
            return billing_date

        billing_date = self.billing.next_invoice_date
        if billing_date and billing_date < date.today():
            billing_date = date.today()
            self.billing.next_invoice_date = billing_date

        return billing_date

    def shift_date(self, magical_argument: date, shift_amount: int) -> date:
        multiply_coefficient = (
            shift_amount * 30
            if self.billing.effective_period == Period.monthly
            else shift_amount * 365
        )
        return_date = magical_argument + datetime.timedelta(days=multiply_coefficient)
        return return_date

    def shifted_payday(
        self, shift_argument: int, user_id: Optional[int] = None
    ) -> date:
        payday = self.payday(user_id)
        return self.shift_date(payday, shift_argument)

    def paid_period(self, shift: ShiftType, user: Optional[int] = None) -> str:
        if shift is ShiftType.Paid:
            start = self.shifted_payday(-1, user)
            end = self.payday(user)
        elif shift is ShiftType.WillBePaid:
            start = self.payday(user)
            end = self.shifted_payday(1, user)
        else:
            raise ValueError("shift cannot be anything but 0 and 1")

        is_monthly = self.billing.effective_period is Period.monthly

        payday_phrase = (
            DateTimeUtils.day_and_month_in_words(start)
            if is_monthly
            else DateTimeUtils.full_date_in_words(start)
        )

        paid_phrase = (
            DateTimeUtils.day_and_month_in_words(end)
            if is_monthly
            else DateTimeUtils.full_date_in_words(end)
        )

        return f"{payday_phrase} – {paid_phrase}"

    def paid_period_from_date(self, date_arg: date, user: Optional[int] = None) -> str:
        start_date = self.payday(user)
        end_date = date.min

        if start_date > date_arg:
            while start_date > date_arg:
                end_date = start_date
                start_date = self.shift_date(start_date, -1)

        elif start_date < date_arg:
            while start_date < date_arg:
                start_date = self.shift_date(start_date, 1)
                end_date = self.shift_date(start_date, 2)
        else:
            end_date = self.shift_date(start_date, 1)

        is_monthly = self.billing.effective_period is Period.monthly

        payday_phrase = (
            DateTimeUtils.day_and_month_in_words(start_date)
            if is_monthly
            else DateTimeUtils.full_date_in_words(start_date)
        )

        paid_phrase = (
            DateTimeUtils.day_and_month_in_words(end_date)
            if is_monthly
            else DateTimeUtils.full_date_in_words(end_date)
        )

        return f"{payday_phrase} - {paid_phrase}"

    @property
    def pure_price_in_eur(self) -> float:
        return CurrencyConverter.convert_to_eur(
            self.billing.price, self.billing.effective_currency
        )

    @property
    def price_in_eur(self) -> float:
        try:
            return self.pure_price_in_eur / float(len(self.billing.members))
        except ZeroDivisionError:
            return self.pure_price_in_eur

    @property
    def effective_type(self) -> SubscriptionType:
        return SubscriptionType.from_str(self.type)

    @property
    def free_slots(self) -> int:
        return self.billing.total_seats - len(self.billing.members)

    def calculate_price_in_eur(self, member_amount: int) -> float:
        return self.pure_price_in_eur / float(member_amount)

    def remove_user(self, user: int):
        try:
            self.billing.members.remove(user)
            self.save()
        except ValueError:
            pass

    class Meta:
        model_key_prefix = "sub"
