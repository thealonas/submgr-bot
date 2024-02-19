import datetime


class DateTimeUtils:
    MONTHS = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]

    @staticmethod
    def day_and_month_in_words(date: datetime.date) -> str:
        return f"{date.day} {DateTimeUtils.MONTHS[date.month - 1]}"

    @staticmethod
    def full_date_in_words(date: datetime.date) -> str:
        return f"{date.day} {DateTimeUtils.MONTHS[date.month - 1]} {date.year} года"
