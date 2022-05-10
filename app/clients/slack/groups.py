import os
import requests
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

COWORKING_SERVER_URL = os.environ.get("COWORKING_SERVER_URL", "http://localhost:5000")


def get_new_session_link():
    res = requests.post(f"{COWORKING_SERVER_URL}/internal/start-coworking-session/")
    if not res.ok:
        return None
    return res.json().get("url", None)


def get_connect_account_token(payload):
    team_id = payload.get("team_id")
    team_domain = payload.get("team_domain")
    user_id = payload.get("user_id")
    if not team_id or not user_id:
        return None
    payload = {
        "platform": "slack",
        "account_id": f"{team_id}|{user_id}",
        "extras": {"team_domain": team_domain},
    }
    res = requests.post(
        f"{COWORKING_SERVER_URL}/internal/connect-account-token/",
        json=payload,
    )
    if not res.ok:
        return None
    return res.json().get("token", None)


def get_atomic_team_groups_for_participants(guild_id, participant_ids):
    res = requests.post(
        f"{COWORKING_SERVER_URL}/internal/atomic-team-groups/",
        json={
            "platform": "slack",
            "server_id": str(guild_id),
            "participant_ids": [str(pid) for pid in participant_ids],
        },
    )
    if not res.ok:
        return None
    return res.json()
