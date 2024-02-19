import datetime

from background_services.repeating_service import RepeatingService


class InvoiceOverwatch(RepeatingService):
    """
    этот сревис должен банить людей которые просрочили оплату на 1 день
    """

    def __init__(self):
        now = datetime.datetime.now()
        super().__init__(
            24 * 60 * 60, datetime.datetime(now.year, now.month, now.day, 10, 0, 0)
        )
        self.name = "InvoiceOverwatch"

    def do_work(self):
        # TODO
        pass
