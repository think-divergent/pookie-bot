import os
import random

from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from common_responses import SIMPLE_RESPONSES
from petname import get_random_name
from discord_client import group_participants
import sqlalchemy
import logging

pookie_teams = {
    "T01D5J87VPH",  # Prod
    "T10RCBTFZ",  # Dev
}

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

bot_token = os.environ.get("SLACK_BOT_TOKEN")
if bot_token:
    app = App(
        token=bot_token,
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
    )
else:
    # Initializes your app with your bot token and signing secret
    client_id, client_secret, signing_secret, db_url, redirect_url = (
        os.environ["SLACK_CLIENT_ID"],
        os.environ["SLACK_CLIENT_SECRET"],
        os.environ["SLACK_SIGNING_SECRET"],
        os.environ["SLACK_APP_DB_URL"],
        os.environ.get(
            "SLACK_REDIRECT_URL", "https://thinkdivergent.io/slack/oauth_redirect"
        ),
    )
    engine = sqlalchemy.create_engine(db_url)
    installation_store = SQLAlchemyInstallationStore(
        client_id=client_id,
        engine=engine,
        logger=logger,
    )
    oauth_state_store = SQLAlchemyOAuthStateStore(
        expiration_seconds=120,
        engine=engine,
        logger=logger,
    )
    try:
        engine.execute("select count(*) from slack_bots")
    except Exception:
        installation_store.metadata.create_all(engine)
        oauth_state_store.metadata.create_all(engine)

    app = App(
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
        installation_store=installation_store,
        oauth_settings=OAuthSettings(
            client_id=client_id,
            client_secret=client_secret,
            state_store=oauth_state_store,
            scopes=[
                "app_mentions:read",
                "channels:manage",
                "channels:history",
                "channels:read",
                "chat:write",
                "groups:write",
                "groups:history",
                "groups:read",
                "im:history",
                "im:read",
                "mpim:history",
                "mpim:read",
                "users:read",
            ],
        ),
    )


@app.event("message")
def handle_message(ack, payload, say, client):
    # import pdb;pdb.set_trace()
    print(payload)
    txt = payload.get("text", "").lower()
    if txt == "<@u01hx3vlcrh> create groups":
        # create teams channels
        ch = payload.get("channel")
        if not ch:
            return
        res = client.conversations_members(channel=ch)
        if not res.get("ok"):
            return
        data = res.data
        members = data.get("members")
        metadata = data.get("response_metadata", {})
        next_cursor = metadata.get("next_cursor")
        while next_cursor:
            res = client.conversations_members(channel=ch, cursor=next_cursor)
            data = res.data
            members += data.get("members")
            metadata = data.get("response_metadata", {})
            next_cursor = metadata.get("next_cursor")
        ack()
        return
    for prompt, responses in SIMPLE_RESPONSES.items():
        if txt.startswith(prompt):
            say(random.choice(responses))
            break
    ack()


def get_channel_members(client, ch):
    res = client.conversations_members(channel=ch)
    if not res.get("ok"):
        return
    data = res.data
    members = data.get("members")
    metadata = data.get("response_metadata", {})
    next_cursor = metadata.get("next_cursor")
    while next_cursor:
        res = client.conversations_members(channel=ch, cursor=next_cursor)
        data = res.data
        members += data.get("members")
        metadata = data.get("response_metadata", {})
        next_cursor = metadata.get("next_cursor")
    return members


def render_members(members):
    return " ".join([f"<@{m}>" for m in members])


@app.event("app_mention")
def handle_mention(ack, payload, say, client):
    user = payload.get("user")
    ack()
    blocks = payload.get("blocks")
    if not blocks:
        return
    elms = blocks[0].get("elements")
    if not elms:
        return
    elms = elms[0].get("elements")
    if not elms or len(elms) < 2:
        return
    cmd = elms[1].get("text", "").strip()
    if cmd == "help":
        say("Here are the available commands:\n\n@Pookie create teams\n\n@Pookie help")
        return
    if cmd == "create teams":
        # create teams for current channel
        if len(elms) != 2:
            return
        channel = payload.get("channel")
        if not channel:
            return
        try:
            res = client.users_info(user=user)
        except SlackApiError as e:
            say("Failed to verify permission to create teams. ")
            logger.error(
                f"Failed to verify permission to create teams. {e.response['error']}"
            )
            return
        is_admin = res.data.get("user", {}).get("is_admin")
        if not is_admin:
            say("Only admins can create teams.")
            return
        members = set(get_channel_members(client, channel))
        bot = elms[0].get("user_id")
        if user in members:
            members.remove(user)
        if bot in members:
            members.remove(bot)
        members = list(members)
        groups = group_participants(members)
        if not groups:
            say("Plaese run this command in a channel with someone else.")
            return
        for group in groups:
            group.append(user)
            team_name = "team-" + get_random_name()
            res = client.conversations_create(name=team_name, is_private=True)
            if res.status_code != 200:
                logger.error(f"Failed to create channel: {res.status_code}")
                say(
                    f"Failed to create channel for {render_members(group)}: {res.status_code}"
                )
                continue
            new_channel = res.get("channel")
            if not new_channel:
                logger.error(f"Failed to create channel: invalid response: {res.data}")
                say(
                    f"Failed create channel for {render_members(group)}: invalid response"
                )
                continue
            new_channel_id = new_channel.get("id")
            try:
                # invite users
                res = client.conversations_invite(
                    channel=new_channel_id, users=",".join(group)
                )
            except SlackApiError as e:
                logger.error(
                    f"Failed to verify permission to create teams. {e.response['error']}"
                )
                say(f"Failed to invite {render_members(group)}")
                continue
            msg = f"""Welcome {render_members(group)} to {team_name}! To get started:\n
1. Introduce yourself! What are you working on right now? What would you like help with? What skills do you have that you can use to help others? \n\n
2. Make an appointment to meet some time during the first week - get to know each other, determine how you best communicate with everyone in your team, and how often you want to check in (be sure to check in at least once a week).\n\n
Need something to find a time for everyone? Try https://whenisgood.net/Create \n\n
Cheers!"""
            client.chat_postMessage(channel=new_channel_id, text=msg)
        say("Done!")
