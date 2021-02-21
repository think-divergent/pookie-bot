import random

import discord
from common_responses import SIMPLE_RESPONSES
import logging
from petname import get_random_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

client = discord.Client()

LANDING_PAD_CHANNEL_ID = 792039815327645736
SIGNUP_MSG_ID = 812836894013915176
ATOMIC_TEAM_CATEGORY_ID = 812829505013809182
OLD_ATOMIC_TEAM_CATEGORY_ID = 812862635333648435
EXISTING_PARTICIPANTS_SET = set()
EXISTING_PARTICIPANTS = []


def group_participants(participants):
    # random participants
    participants = [x for x in participants]
    random.shuffle(participants)
    if len(participants) > 12:
        group_size = 4
    elif len(participants) > 6:
        group_size = 3
    else:
        group_size = 2
    groups = []
    new_group = []
    for participant in participants:
        new_group.append(participant)
        if len(new_group) == group_size:
            groups.append(new_group)
            new_group = []
    if len(new_group) == 1:
        # if we have more than one group
        if len(groups):
            if group_size == 4:
                # move a person from a 4 people group
                new_group = [groups[-1][3], new_group[0]]
                groups[-1] = groups[-1][:3]
                groups.append(new_group)
            else:
                # add to an existing group
                groups[-1].append(new_group[0])
        else:
            groups.append(new_group)
    elif len(new_group) > 1:
        groups.append(new_group)
    return groups


async def make_groups():
    channel = client.get_channel(LANDING_PAD_CHANNEL_ID)
    msg = await channel.fetch_message(SIGNUP_MSG_ID)
    reaction = None
    for rec in msg.reactions:
        if rec.emoji == "✅":
            reaction = rec
            break
    if not reaction:
        return
    participants = await reaction.users().flatten()
    groups = group_participants(participants)
    category = client.get_channel(ATOMIC_TEAM_CATEGORY_ID)
    archive_category = client.get_channel(OLD_ATOMIC_TEAM_CATEGORY_ID)
    for channel in category.channels:
        await channel.edit(category=archive_category)
    txt_channel_perm = discord.PermissionOverwrite()
    txt_channel_perm.send_messages = True
    txt_channel_perm.read_messages = True
    txt_channel_perm.add_reactions = True
    voice_channel_perm = discord.PermissionOverwrite()
    voice_channel_perm.view_channel = True
    voice_channel_perm.speak = True
    voice_channel_perm.connect = True
    voice_channel_perm.stream = True
    for idx, group in enumerate(groups):
        group_name = f"team-{get_random_name()}"
        txt_channel = await category.create_text_channel(group_name + "-text")
        voice_channel = await category.create_voice_channel(group_name + "-voice")
        for participant in group:
            try:
                await txt_channel.set_permissions(
                    participant, overwrite=txt_channel_perm
                )
                await voice_channel.set_permissions(
                    participant, overwrite=voice_channel_perm
                )
            except Exception as e:
                logger.exception(e)
        # mentions = " ".join([x.mention for x in group])
        await txt_channel.send(
            f"Welcome to {group_name}! This is your team for the next two weeks!"
            " Get to know each other, share what you'd like to work on next and one concrete thing "
            "that you can use help with!"
        )


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    txt = message.content.lower()
    if txt == "create_groups":
        if message.author.id != 209669511517962241:
            return
        print("Creating Groups")
        await make_groups()
        print("Created Groups")
        return
    for prompt, responses in SIMPLE_RESPONSES.items():
        if txt.startswith(prompt):
            await message.channel.send(random.choice(responses))
            return
