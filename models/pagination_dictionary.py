class PaginationDictionary(dict):
    def forward(self, user_id: int):
        if self.get(user_id) is None:
            self[user_id] = 0

        self[user_id] += 1

    def backward(self, user_id: int):
        if self.get(user_id) is None:
            self[user_id] = 0
            return

        if self[user_id] == 0:
            return

        if self[user_id] < 0:
            self[user_id] = 0
            return

        self[user_id] -= 1
