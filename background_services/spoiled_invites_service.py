import datetime

from background_services.repeating_service import RepeatingService
from database_models.invite import Invite


class SpoiledInvitesService(RepeatingService):
    def __init__(self):
        now = datetime.datetime.now()
        super().__init__(
            12 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 12, 0, 0)
        )
        self.name = "SpoiledInvitesService"

    def do_work(self):
        invites = Invite.find().all()
        invites = [i for i in invites if i.spoiled and i.db().ttl(i.key()) == -1]

        if not invites:
            return

        for invite in invites:
            invite.expire(24 * 60 * 60)
            invite.save()
