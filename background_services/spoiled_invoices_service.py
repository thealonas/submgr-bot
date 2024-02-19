import datetime

from background_services.repeating_service import RepeatingService
from database_models.invoice import Invoice


class SpoiledInvoicesService(RepeatingService):
    def __init__(self):
        now = datetime.datetime.now()
        super().__init__(
            12 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 12, 0, 0)
        )
        self.name = "SpoiledInvitesService"

    def do_work(self):
        invoices = Invoice.find().all()
        invoices = [i for i in invoices if i.paid and i.db().ttl(i.key()) == -1]

        if not invoices:
            return

        for invite in invoices:
            invite.expire(30 * 60 * 60 * 24)
            invite.save()
