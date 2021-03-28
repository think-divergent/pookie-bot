import os
import random

from slack_bolt import App
from slack_bolt.oauth.oauth_settings import OAuthSettings
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from slack_sdk.oauth.state_store.sqlalchemy import SQLAlchemyOAuthStateStore
from common_responses import SIMPLE_RESPONSES
import sqlalchemy
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

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
            "channels:history",
            "channels:read",
            "chat:write",
            "groups:history",
            "groups:read",
            "im:history",
            "im:read",
            "mpim:history",
            "mpim:read",
        ],
    ),
)

# Listens to incoming messages that contains Example, send a buttonm, receive events
"""
@app.message("Example")
def message_hello(message, say):
    # say() sends a message to the channel where the event was triggered
    say(
        blocks=[
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"Hey there <@{message['user']}>!"},
                "accessory": {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Pet me!"},
                    "action_id": "button_click"
                }
            }
        ],
        text=f"Hey there <@{message['user']}>!"
    )

@app.action("button_click")
def action_button_click(body, ack, say):
    # Acknowledge the action
    ack()
    #say(f"<@{body['user']['id']}> clicked the button")
"""


@app.event("message")
def handle_message(payload, say, client):
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

        return
    for prompt, responses in SIMPLE_RESPONSES.items():
        if txt.startswith(prompt):
            say(random.choice(responses))
