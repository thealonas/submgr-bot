from typing import List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import phrases
from database_models.invite import Invite
from models.pagination_dictionary import PaginationDictionary
from modules.pagination_module import PaginationModule
from utils import keyboard_utils
from utils.callback_utils import ConfigurableCallbackList, CallbackList


class InviteModule:
    ITEMS_PER_PAGE = 4

    current_pages: PaginationDictionary[int, int] = PaginationDictionary()

    @staticmethod
    def generate_keyboard(
        invites: List[Invite], user_id: int, able_to_create_invite: bool
    ) -> InlineKeyboardMarkup:
        invites = [i for i in invites if not i.used]

        keyboard = []

        create_invite_button = InlineKeyboardButton(
            "🐁 создать инвайт", callback_data=CallbackList.create_invite
        )
        back_button = InlineKeyboardButton(
            phrases.go_back, callback_data=CallbackList.profile
        )

        if len(invites) == 0 or not invites:
            keyboard.append([keyboard_utils.no_elements_button])
            if able_to_create_invite:
                keyboard.append([create_invite_button])
            keyboard.append([back_button])
            return InlineKeyboardMarkup(keyboard)

        invites = sorted(invites, key=lambda inv: inv.issue_date)

        keyboard = []

        left_button_callback = CallbackList.invites_pagination_backward
        right_button_callback = CallbackList.invites_pagination_forward
        overview_callback = ConfigurableCallbackList.invite_overview

        page = InviteModule.current_pages.get(user_id, 0)

        start_index = page * InviteModule.ITEMS_PER_PAGE
        end_index = start_index + InviteModule.ITEMS_PER_PAGE

        for i in range(start_index, end_index, 2):
            row = []
            for j in range(i, min(i + 2, len(invites))):
                invite = invites[j]
                button_text = f"📮 {invite.id}"
                callback_data = overview_callback.box_value(invite.id)
                row.append(
                    InlineKeyboardButton(button_text, callback_data=callback_data)
                )
            keyboard.append(row)

        pagination = PaginationModule.get_pagination_buttons(
            invites, page, right_button_callback, left_button_callback, end_index
        )

        if pagination:
            keyboard.append(pagination)

        if able_to_create_invite:
            keyboard.append([create_invite_button])

        keyboard.append([back_button])

        return InlineKeyboardMarkup(keyboard)
