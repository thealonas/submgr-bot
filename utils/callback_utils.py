import re


class InlineCallback:
    key: str

    def __init__(self, key: str):
        self.key = key

    def box_value(self, value: str):
        return f"{self.key} {value}"

    def extract_value(self, string: str) -> str:
        return string.split(self.key)[1].strip()

    def matches(self, value: str) -> bool:
        match = re.search(r"\b" + re.escape(self.key) + r"\b", value)
        if match:
            return True
        return False


class ConfigurableCallbackList:
    sub_credential = InlineCallback("subcr")

    my_sub_overview_faq = InlineCallback("mysodesc")
    my_sub_overview_process = InlineCallback("mysoproc")
    my_sub_overview_join = InlineCallback("mysojoin")
    my_sub_overview_join_confirm = InlineCallback("mysojoinconf")
    my_sub_overview_leave = InlineCallback("mysoleave")
    my_sub_overview_leave_confirm = InlineCallback("mysoleaveconf")
    my_sub_overview = InlineCallback("myso")

    available_sub_overview_faq = InlineCallback("avsodesc")
    available_sub_overview_process = InlineCallback("avsoproc")
    available_sub_overview_join = InlineCallback("avsojoin")
    available_sub_overview_join_confirm = InlineCallback("avsojoinconf")
    available_sub_overview_leave = InlineCallback("avsoleave")
    available_sub_overview_leave_confirm = InlineCallback("avsoleaveconf")
    available_sub_overview = InlineCallback("avso")

    invoice_overview = InlineCallback("invceo")
    invoice_overview_notify = InlineCallback("invceonotif")

    invoice_pay = InlineCallback("invcepay")
    invoice_pay_notify = InlineCallback("invcepaynotif")

    invoice_pay_confirm = InlineCallback("invcepayconf")
    invoice_pay_confirm_notify = InlineCallback("invcepayconfnotif")

    invite_overview = InlineCallback("invo")


class CallbackList:
    available_subs_list = "available_subs_list"
    available_subs_list_pagination_forward = "available_subs_list_pagination_forward"
    available_subs_list_pagination_backward = "available_subs_list_pagination_backward"

    my_subs_list = "my_subs_list"
    my_subs_list_pagination_forward = "my_subs_list_pagination_forward"
    my_subs_list_pagination_backward = "my_subs_list_pagination_backward"

    profile = "profile"

    invoices = "invoices"
    invoices_pagination_forward = "invoices_pagination_forward"
    invoices_pagination_backward = "invoices_pagination_backward"

    invites = "invites"
    invites_pagination_forward = "invites_pagination_forward"
    invites_pagination_backward = "invites_pagination_backward"

    create_invite = "create_invite"

    request_sub = "request_sub"

    no_elements = "no_subs"
