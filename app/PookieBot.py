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
    slack_app.start(port=3300)


if __name__ == "__main__":
    slack_thread = threading.Thread(target=run_slack_client)
    slack_thread.start()
    run_discord_client()
