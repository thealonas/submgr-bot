from datetime import date
from typing import Optional, List

import redis_om
import telegram

from database_models.base_model import BaseModel, BaseEmbeddedModel
from database_models.invite import Invite
from database_models.invoice import Invoice
from database_models.subscription import Subscription
from enums.list_type import ListType


class UserSubscriptionBilling(BaseEmbeddedModel):
    sub_id: int
    joined: Optional[date]
    date: Optional[date]
    internal_id: Optional[str]

    class Meta:
        embedded = True


class User(BaseModel):
    invite_limit: int = 10
    id: int = redis_om.Field(index=True, primary_key=True, default=0)
    name: str
    admin: bool = False
    email: Optional[str]
    banned: bool = False
    ban_reason: Optional[str]
    warnings: int = 0
    billing: List[UserSubscriptionBilling] = []
    referral: Optional[int] = None

    def __get_user_subs(self) -> List[Subscription]:
        subs = [i for i in Subscription.find().all() if i.is_active]
        output = []
        for sub in subs:
            if self.id not in sub.billing.members:
                continue
            output.append(sub)
        return output

    def get_subs(self, list_type: ListType) -> List[Subscription]:
        match list_type:
            case ListType.MY_SUBS:
                return self.__get_user_subs()
            case ListType.AVAILABLE_SUBS:
                return self.__get_available_subs()
            case _:
                raise ValueError("Invalid list type")

    def get_invoices(self) -> List[Invoice]:
        invoices = Invoice.find(Invoice.user == self.id).all()
        if not invoices:
            return []

        return invoices

    def get_invites(self, only_unused: bool = False) -> List[Invite]:
        invites = Invite.find(Invite.from_user == self.id).all()

        if only_unused:
            invites = [invite for invite in invites if not invite.used]

        if not invites:
            return []

        return invites

    def get_display_invites(self) -> List[Invite]:
        invites = self.get_invites()
        invites = [invite for invite in invites if not invite.spoiled]

        return invites

    def get_sub_period(self, sub: int) -> date:
        period = None
        for i in self.billing:
            if i.sub_id == sub:
                period = i.date
                break

        if not period:
            raise RuntimeError(f"Subscription {sub} not found in billing")

        return period

    def set_sub_period(self, sub: int, period: date):
        for i in self.billing:
            if i.sub_id == sub:
                i.date = period
                i.save()
                break

        self.billing.append(UserSubscriptionBilling(sub_id=sub, date=period))

        self.save()

    def __get_available_subs(self) -> List[Subscription]:
        subs = Subscription.find().all()
        all_available_subs: List[Subscription] = []

        user_subs: List[int] = []

        for sub in subs:
            if not sub.is_active:
                continue
            if self.id in sub.billing.members:
                user_subs.append(sub.id)
                continue
            if sub.is_full:
                continue
            all_available_subs.append(sub)

        output = []

        for sub in all_available_subs:
            if not sub.forbidden_with:
                output.append(sub)
                continue
            is_forbid = False
            for forbidden in sub.forbidden_with:
                if forbidden in user_subs:
                    is_forbid = True
            if not is_forbid:
                output.append(sub)
        return output

    def can_access_password_info(self, sub_id: int) -> bool:
        invoices: List[Invoice] = Invoice.find(Invoice.user == self.id).all()
        if not invoices:
            return False

        all_subs: List[List[int]] = [
            [b.sub_id for b in i.subscriptions] for i in invoices
        ]
        unique_subs = []

        for sub_array in all_subs:
            for sub in sub_array:
                if sub not in unique_subs:
                    unique_subs.append(sub)

        if sub_id not in unique_subs:
            return False

        at_least_one_paid = False

        for invoice in invoices:
            if not invoice.paid and invoice.pay_till < date.today():
                return False

            if invoice.paid:
                at_least_one_paid = True

        if not at_least_one_paid:
            return False

        return True

    @staticmethod
    def get_by_id(user_id: int) -> Optional["User"]:
        query = User.find(User.id == user_id).all()
        if query:
            return query[0]
        return None

    @staticmethod
    def create_default(user: telegram.User, referral: Optional[int] = None) -> "User":
        user = User(
            id=user.id,
            name=user.full_name,
            referral=referral,
        )
        user.save()
        return user

    def can_join_forbidden_with(self, sub_id: int) -> int:
        """
        0 if can join
        else returns subscription id
        """
        subs = self.__get_user_subs()

        if not subs:
            return 0

        for sub in subs:
            if sub.forbidden_with is not None and sub_id in sub.forbidden_with:
                return sub_id
        return 0

    def ban(self):
        self.banned = True
        self.save()

    def set_joined_date(self, sub_id: int, joined: Optional[date] = date.today()):
        for i in self.billing:
            if i.sub_id == sub_id:
                i.joined = joined
                i.save()
                break

        self.billing.append(UserSubscriptionBilling(sub_id=sub_id, joined=joined))
        self.save()

    def has_invoice(self, sub: Optional[int] = None) -> bool:
        if not sub:
            return len([i for i in self.get_invoices() if i.paid]) > 0

        return (
            len([i for i in self.get_invoices() if i.has_subscription(sub) and i.paid])
            > 0
        )

    class Meta:
        model_key_prefix = "user"
