from enum import Enum


class SubscriptionType(Enum):
    individual = 0
    group = 1

    @staticmethod
    def from_str(subscription_type: str) -> "SubscriptionType":
        if subscription_type == "individual":
            return SubscriptionType.individual
        elif subscription_type == "group":
            return SubscriptionType.group
        else:
            raise ValueError(f"Invalid SubscriptionType: {subscription_type}")

    def __str__(self) -> str:
        match self:
            case SubscriptionType.individual:
                return "individual"
            case SubscriptionType.group:
                return "group"
