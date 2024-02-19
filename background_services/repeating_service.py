import asyncio
import logging
from datetime import datetime, timedelta
from threading import Thread

import sentry_sdk

import debug


class RepeatingService:
    name: str = "RepeatingService"
    _thread: Thread

    def __init__(self, interval_seconds: int, start_time: datetime):
        self.start_time = start_time
        self.interval_seconds = interval_seconds
        self._thread = Thread(target=asyncio.run, args=(self.__run(),))

    def start(self):
        self._thread.start()

    def do_work(self):
        return

    async def do_work_async(self):
        return

    async def __run(self):
        # Расчет времени до следующего запуска
        now = datetime.now()
        future = datetime(
            now.year, now.month, now.day, self.start_time.hour, self.start_time.minute
        )

        if now > future:
            # Если время уже прошло, переходим на следующий день
            future += timedelta(days=1)

        target_time = future - now

        logging.info(
            f"[{self.name}] waiting for {target_time}\nfuture: {future}\nnow: {now}"
        )

        # Ожидание до начала времени

        if debug.debug:
            logging.info("DEBUG: skipping waiting\n")
        else:
            await asyncio.sleep(target_time.total_seconds())

        try:
            await self.do_work_async()
            self.do_work()
            print(f"work {self.name} complete")
            await asyncio.sleep(self.interval_seconds)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise
