import os
import asyncio
from discord_slash.utils.manage_commands import (
    get_all_commands,
    add_slash_command,
    remove_all_commands,
)

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
# Pookie ID
POOKIE_USER_ID = os.environ.get("POOKIE_USER_ID", 795343874049703986)
# remove all old commands
asyncio.run(remove_all_commands(POOKIE_USER_ID, DISCORD_TOKEN))
# Create the command
asyncio.run(
    add_slash_command(
        POOKIE_USER_ID,
        DISCORD_TOKEN,
        None,
        "start-session",
        "Start a coworking session in 5 minutes",
    )
)
asyncio.run(
    add_slash_command(
        POOKIE_USER_ID,
        DISCORD_TOKEN,
        None,
        "update-availability",
        "Update your availability for Atomic Teams",
    )
)
# list existing commands
asyncio.run(get_all_commands(POOKIE_USER_ID, DISCORD_TOKEN))
