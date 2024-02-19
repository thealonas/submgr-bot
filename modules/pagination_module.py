from typing import List

from telegram import InlineKeyboardButton


class PaginationModule:
    @staticmethod
    def get_pagination_buttons(
        objects: List,
        page: int,
        right_callback: str,
        left_callback: str,
        end_index: int,
    ) -> List[InlineKeyboardButton]:
        if len(objects) > 4:
            nav_buttons = []

            if page > 0:
                nav_buttons.append(
                    InlineKeyboardButton("⬅️", callback_data=left_callback)
                )

            if end_index < len(objects):
                nav_buttons.append(
                    InlineKeyboardButton("➡️", callback_data=right_callback)
                )

            return nav_buttons
        return []
