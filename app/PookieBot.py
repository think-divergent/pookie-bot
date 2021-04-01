import logging
import os
import threading


from discord_client import client as discord_app
from slack_client import app as slack_app

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
logging.basicConfig(level=logging.INFO)


def run_discord_client():
    discord_app.run(DISCORD_TOKEN)


def run_slack_client():
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if app_token:
        from slack_bolt.adapter.socket_mode import SocketModeHandler

        SocketModeHandler(slack_app, app_token).start()
    else:
        slack_app.start(port=3300)


if __name__ == "__main__":
    if os.environ.get("SLACK_ONLY"):
        run_slack_client()
    elif os.environ.get("DISCORD_ONLY"):
        run_discord_client()
    else:
        slack_thread = threading.Thread(target=run_slack_client)
        slack_thread.start()
        run_discord_client()
