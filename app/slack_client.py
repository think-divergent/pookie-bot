import os
import random

from slack_bolt import App
from slack_sdk.errors import SlackApiError
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from common_responses import SIMPLE_RESPONSES
from petname import get_random_name
from clients.discord.groups import group_participants
from clients.slack.groups import get_connect_account_token
from server_config import get_slack_server_config
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
                "commands",
            ],
        ),
    )


@app.event("message")
def handle_message(ack, payload, say, client):
    # import pdb;pdb.set_trace()
    txt = payload.get("text", "").lower()
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
    logger.debug("app mention")
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
    if cmd == "team_join_test":
        handle_team_join(ack, payload, say, client)
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


def _perform_reactions(user, client, server_config, reactions, say):
    for reaction in reactions:
        template = reaction.get("template", "Hello {user}! Welcome to {community}!")
        community = server_config.get("community_name", "this community")
        community_manager_id = server_config.get("community_manager_id")
        if community_manager_id:
            community_manager = f"<@{community_manager_id}>"
        else:
            community_manager = ""
        intro_channel_id = server_config.get("intro_channel_id")
        if intro_channel_id:
            intro_channel = f"<#{intro_channel_id}>"
        else:
            intro_channel = "the introduction channel"
        formatted_msg = template.format(
            user=f"<@{user}>",
            community=community,
            community_manager=community_manager,
            intro_channel=intro_channel,
        )
        logger.debug(formatted_msg)
        if "image_attachment" in reaction:
            blocks = [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": formatted_msg,
                    },
                },
                {
                    "type": "image",
                    "image_url": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                    "alt_text": "hello",
                },
            ]
        else:
            blocks = None
        if reaction.get("type") == "say":
            logger.debug("saying: " + formatted_msg)
            if blocks:
                say(blocks=blocks, text=formatted_msg)
            else:
                say(formatted_msg)
        elif reaction.get("type") == "dm":
            logger.debug("dming:" + formatted_msg)
            if blocks:
                client.chat_postMessage(channel=user, text=formatted_msg, blocks=blocks)
            else:
                client.chat_postMessage(channel=user, text=formatted_msg)


@app.event("team_join")
def handle_team_join(ack, payload, say, client):
    try:
        logger.debug(f"team_join: {payload}")
        ack()
        user = payload.get("user", {}).get("id")
        if not user:
            logger.debug("user not found")
            return
        server_config = get_slack_server_config(payload)
        if not server_config:
            logger.debug("server config not found")
            return
        team_join_config = server_config.get("team_join_config", {})
        if not team_join_config:
            logger.debug("no team join config")
            return
        _perform_reactions(
            user, client, server_config, team_join_config.get("reactions", []), say
        )
    except Exception as e:
        logger.exception(e)


@app.event("member_joined_channel")
def handle_member_joined_channel(ack, payload, say, client):
    try:
        logger.debug(f"member_joined_channel: {payload}")
        ack()
        user = payload.get("user")
        if not user:
            logger.debug("user not found")
            return
        server_config = get_slack_server_config(payload)
        if not server_config:
            logger.debug("server config not found")
            return
        channel = payload.get("channel")
        member_join_channel_config = server_config.get("member_join_channel_config", {})
        if channel not in member_join_channel_config:
            logger.debug("channel not in join config")
            return
        _perform_reactions(
            user,
            client,
            server_config,
            member_join_channel_config[channel].get("reactions", []),
            say,
        )
    except Exception as e:
        logger.exception(e)


@app.command("/update-availability")
def command(ack, payload, body, respond):
    ack()
    team_id = payload.get("team_id")
    if not team_id:
        return
    # check for atomic team sign up message
    server_config = get_slack_server_config(payload)
    if not server_config:
        return respond(
            "Looks like this slack space is not connected to an Alliance yet."
        )
    slug = server_config.get("alliance_slug")
    if not slug:
        return respond(
            "Looks like this slack space is not connected to an Alliance yet."
        )
    # new member signed up for atomic team
    token = get_connect_account_token(payload)
    if not token:
        return respond("Something went wrong...Plaese try again later.")
    url = f"https://ThinkDivergent.com/a/{slug}/atomic-teams/availability/{token}?v=2"
    server_name = server_config["community_name"]
    respond(
        {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"Welcome to Atomic Teams at {server_name}!\n"
                            "Set your availability for a weekly meet up with your team with the link below\n"
                            f"<{url}|{url[8:65]}...>"
                        ),
                    },
                },
                {
                    "type": "image",
                    "title": {
                        "type": "plain_text",
                        "text": f"Set availability for {server_config['community_name']} Atomic Teams",
                    },
                    "image_url": "https://cdn.thinkdivergent.com/video/set-availability.gif",
                    "alt_text": "set availability",
                },
            ]
        }
    )
