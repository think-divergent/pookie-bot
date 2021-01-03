import random

import discord
from common_responses import SIMPLE_RESPONSES

client = discord.Client()

@client.event
async def on_ready():
    print('We have logged in as {0.user}'.format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    txt = message.content.lower()
    for prompt, responses in SIMPLE_RESPONSES.items()
        if txt.startswith(prompt):
            await message.channel.send(random.choice(responses))
            return

