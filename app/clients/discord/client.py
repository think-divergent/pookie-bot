import os
import discord
from discord.ext import commands
from discord_slash import SlashCommand

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
client = commands.Bot(command_prefix="", intents=intents)
slash = SlashCommand(client)

POOKIE_USER_ID = os.environ.get("POOKIE_USER_ID", 795343874049703986)
