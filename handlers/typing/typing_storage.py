from enum import Enum


class TypingStage(Enum):
    available_handlers_contact = 0


class TypingStorage(dict):
    def add_user(self, user: int, stage: TypingStage):
        self[user] = stage

    def remove_user(self, user: int):
        if user in self:
            del self[user]
