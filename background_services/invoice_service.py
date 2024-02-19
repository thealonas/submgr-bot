import datetime
import logging
from typing import List

from background_services.repeating_service import RepeatingService
from database_models.invoice import Invoice, InvoiceSubscriptionInfo
from database_models.subscription import Subscription
from database_models.user import User
from enums.list_type import ListType
from enums.subscription_type import SubscriptionType


class InvoiceService(RepeatingService):
    def __init__(self):
        now = datetime.datetime.now()
        super().__init__(
            24 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 11, 55, 0)
        )
        self.name = "InvoiceService"

    def do_work(self):
        # булы оно не индексит
        subs: List[Subscription] = [
            i for i in Subscription.find().all() if i and i.is_active
        ]

        users: List[User] = [i for i in User.find().all()]

        if not subs:
            return

        for sub in subs:
            if sub.reserve and sub.effective_type is SubscriptionType.individual:
                raise RuntimeError(f"Individual subscription {sub.id} can't be reserve")

            if sub.reserve and sub.free_slots > 0:
                continue
            elif sub.reserve:
                sub.billing.next_invoice_date = datetime.date.today()
                sub.save()

        for user in users:
            user_subs: List[Subscription] = user.get_subs(ListType.MY_SUBS)
            invoice_info: List[InvoiceSubscriptionInfo] = []

            for sub in user_subs:
                if (
                    sub.effective_type is not SubscriptionType.individual
                    and not sub.billing.next_invoice_date
                ):
                    continue

                is_payday = sub.payday(user.id) <= datetime.date.today()
                if is_payday:
                    invoice_info.append(
                        InvoiceSubscriptionInfo(
                            sub_id=sub.id,
                            period_start_date=sub.payday(user.id),
                            period_end_date=sub.shifted_payday(1, user.id),
                            price=sub.price_in_eur,
                        )
                    )

            if invoice_info:
                Invoice(
                    invoice_id=Invoice.generate_invoice_id(),
                    user=user.id,
                    date=datetime.date.today(),
                    pay_till=datetime.date.today() + datetime.timedelta(days=2),
                    subscriptions=invoice_info,
                    paid=False,
                ).save()

        InvoiceService.__update_subscriptions_billings(subs, users)

    @staticmethod
    def __update_subscriptions_billings(subs: List[Subscription], users: List[User]):
        today = datetime.date.today()
        for sub in subs:
            if sub.reserve and sub.free_slots > 0:
                continue
            elif sub.reserve and sub.effective_type is SubscriptionType.individual:
                raise RuntimeError(
                    f"sub {sub.id} cannot be individual and reserved at the same time"
                )
            match sub.effective_type:
                case SubscriptionType.group:
                    if sub.payday() > today:
                        continue
                    sub.billing.next_invoice_date = sub.shifted_payday(1)
                    sub.save()

                case SubscriptionType.individual:
                    for user in [i for i in users if i.id in sub.billing.members]:
                        if sub.payday(user.id) > today:
                            continue
                        user.set_sub_period(
                            sub.id, sub.shift_date(user.get_sub_period(sub.id), 1)
                        )

    @staticmethod
    def invoice_individual_sub_member(sub: Subscription, user_id: int):
        user: User = User.find(User.id == user_id).all()[0]

        if sub.effective_type is not SubscriptionType.individual:
            raise RuntimeError(f"Subscription {sub.id} is not individual")

        if user.has_invoice(sub.id):
            return

        user.set_sub_period(sub.id, datetime.date.today())

        Invoice(
            invoice_id=Invoice.generate_invoice_id(),
            user=user.id,
            date=datetime.date.today(),
            pay_till=datetime.date.today() + datetime.timedelta(days=2),
            subscriptions=[
                InvoiceSubscriptionInfo(
                    sub_id=sub.id,
                    period_start_date=sub.payday(user.id),
                    period_end_date=sub.shifted_payday(1, user.id),
                    price=sub.pure_price_in_eur,
                )
            ],
            paid=False,
        ).save()
