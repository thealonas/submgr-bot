from telegram.error import TelegramError

from database_models.subscription import Subscription
from database_models.user import User
from models.bot_context import BotContext


class SubscriptionNotifier:
    notify_message_member_joined = (
        "<b>{SUB}: новый участник 🤝</b>\n\n"
        "теперь в подписке {COUNT_WITH_DECLENSION}\n\n"
        "<b>цена подписки изменена с</b> €<code>{OLD_PRICE}</code> на €<code>{NEW_PRICE}</code>"
    )

    notify_message_member_left = (
        "<b>{SUB}: участник вышел из подписки 🫰</b>\n\n"
        "теперь в подписке {COUNT_WITH_DECLENSION}\n\n"
        "<b>цена подпки изменена с</b> €<code>{OLD_PRICE}</code> на €<code>{NEW_PRICE}</code>"
    )

    @staticmethod
    def __find_sub(sub: int) -> Subscription:
        subs = Subscription.find(Subscription.id == sub).all()
        if not subs:
            raise RuntimeError(f"Subscription {sub} not found")

        sub: Subscription = subs[0]
        return sub

    @staticmethod
    def count_with_declension(count: int) -> str:
        msg = f"{count} "
        last_digit = count % 10

        if last_digit == 1:
            msg += "участник"
            return msg

        if last_digit in [2, 3, 4]:
            msg += "участника"
            return msg

        msg += "участников"
        return msg

    @staticmethod
    async def notify_member_joined(ctx: BotContext, sub_id: int, new_member_id: int):
        sub = SubscriptionNotifier.__find_sub(sub_id)

        if sub.reserve:
            return

        if len(sub.billing.members) <= 1:
            return

        old_price = f"{sub.calculate_price_in_eur(len(sub.billing.members) - 1):.2f}"
        new_price = f"{sub.price_in_eur:.2f}"

        message = (
            SubscriptionNotifier.notify_message_member_joined.replace("{SUB}", sub.name)
            .replace("{OLD_PRICE}", old_price)
            .replace("{NEW_PRICE}", new_price)
            .replace(
                "{COUNT_WITH_DECLENSION}",
                SubscriptionNotifier.count_with_declension(len(sub.billing.members)),
            )
        )

        for member in sub.billing.members:
            if member == new_member_id:
                continue

            if not User.find(User.id == member).all():
                continue

            try:
                await ctx.send_message(message, chat_id=member)
            except TelegramError:
                pass

    @staticmethod
    async def notify_member_left(ctx: BotContext, sub_id: int, member_id: int):
        sub = SubscriptionNotifier.__find_sub(sub_id)

        if sub.reserve:
            return

        if len(sub.billing.members) < 1:
            return

        old_price = f"{sub.calculate_price_in_eur(len(sub.billing.members) + 1):.2f}"
        new_price = f"{sub.price_in_eur:.2f}"

        message = (
            SubscriptionNotifier.notify_message_member_left.replace("{SUB}", sub.name)
            .replace("{OLD_PRICE}", old_price)
            .replace("{NEW_PRICE}", new_price)
            .replace(
                "{COUNT_WITH_DECLENSION}",
                SubscriptionNotifier.count_with_declension(len(sub.billing.members)),
            )
        )

        for member in sub.billing.members:
            if member == member_id:
                continue

            if not User.find(User.id == member).all():
                continue

            try:
                await ctx.send_message(message, chat_id=member)
            except TelegramError:
                pass
