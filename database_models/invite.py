import datetime
import random
import string
from datetime import date, timedelta
from typing import Optional

import redis_om

from database_models.base_model import BaseModel

life_time_in_days: int = 2


class Invite(BaseModel):
    id: str = redis_om.Field(index=True, primary_key=True)
    from_user: int = redis_om.Field(index=True)
    used: bool
    issue_date: date
    used_by: Optional[int] = redis_om.Field(index=True)

    def is_expired(self) -> bool:
        return date.today() > self.issue_date + timedelta(days=life_time_in_days)

    def get_expiry_date(self) -> date:
        return self.issue_date + timedelta(days=life_time_in_days)

    def get_url(self) -> str:
        return f"https://t.me/submgr_bot?start={self.id}"

    def use_invite(self, user: int):
        self.used = True
        self.used_by = user
        self.save()

    @staticmethod
    def generate_id() -> str:
        return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

    @staticmethod
    def create_invite(user: int) -> "Invite":
        invite = Invite(
            id=Invite.generate_id(),
            from_user=user,
            issue_date=date.today(),
            used=False,
            used_by=None,
        )
        return invite

    @property
    def spoiled(self) -> bool:
        if self.used:
            return False

        return (
            self.issue_date + datetime.timedelta(days=life_time_in_days) < date.today()
        )

    class Meta:
        model_key_prefix = "invite"
