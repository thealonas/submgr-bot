from enum import Enum


class Period(Enum):
    monthly = 0
    yearly = 1

    @staticmethod
    def from_str(period: str) -> "Period":
        if period == "monthly":
            return Period.monthly
        elif period == "yearly":
            return Period.yearly
        else:
            raise ValueError(f"Invalid period: {period}")
