from database_models.invite import Invite


def try_find_invite(invite_id: str) -> Invite | None:
    all_invites = Invite.find(Invite.id == invite_id).all()
    if len(all_invites) > 0:
        return all_invites[0]
    return None
