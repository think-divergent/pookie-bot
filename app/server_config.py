import json
import requests
import os
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

COWORKING_SERVER_URL = os.environ.get("COWORKING_SERVER_URL", "http://localhost:5000")


def _get_server_config(platform, community_id):
    if not platform or not community_id:
        return None
    try:
        res = requests.get(
            f"{COWORKING_SERVER_URL}/internal/external-community-config/{platform}/{community_id}",
        )
        if not res.ok:
            return None
    except Exception as e:
        logger.exception(e)
        return None
    config = res.json()
    logger.debug(f"{platform} config for {community_id} {json.dumps(config, indent=4)}")
    return config


def save_server_config(platform, community_id, config):
    res = requests.post(
        f"{COWORKING_SERVER_URL}/internal/external-community-config/{platform}/{community_id}",
        json=config,
    )
    if not res.ok:
        logging.error(f"Failed to save server config: {res}")
        return False
    return True


def get_discord_server_config(guild_id):
    return _get_server_config("discord", guild_id)


def get_slack_server_config(payload):
    # depending on the payload the team could either be team_id, team or user.team_id
    team = payload.get("team", payload.get("team_id"))
    if not team:
        team = payload.get("user", {}).get("team_id")
    return _get_server_config("slack", team)
