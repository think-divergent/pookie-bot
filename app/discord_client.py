import asyncio
import os
import datetime
import random
import hashlib

import discord
from discord.ext import commands
from discord_slash import SlashCommand, SlashContext
from common_responses import SIMPLE_RESPONSES
import logging
from petname import get_random_name

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

intents = discord.Intents.default()
client = commands.Bot(command_prefix="", intents=intents)
slash = SlashCommand(client)

EMOJI_CHECK_MARK = "✅"
POOKIE_USER_ID = os.environ.get("POOKIE_USER_ID", 795343874049703986)
LANDING_PAD_CHANNEL_ID = 792039815327645736
SIGNUP_MSG_ID = 812836894013915176
ATOMIC_TEAM_CATEGORY_ID = 812829505013809182
OLD_ATOMIC_TEAM_CATEGORY_ID = 812862635333648435
THINK_DIVERGENT_GUILD = 742405250731999273
EXISTING_PARTICIPANTS_SET = set()
EXISTING_PARTICIPANTS = []

# TODO save this to DB somewhere
GUILD_2_COLLAB_SESSION_CAT_ID = {
    806941792532168735: 810096286492655646,  # ASI
    699390284416417842: 815777518699020318,  # SS
    742405250731999273: 816071249222041600,  # TD
}


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
                # move 2 people from two 4 people group
                new_group = [groups[-2][3], groups[-1][3], new_group[0]]
                groups[-1] = groups[-1][:3]
                groups[-2] = groups[-2][:3]
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
        if rec.emoji == EMOJI_CHECK_MARK:
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
        mentions = " ".join([x.mention for x in group])
        await txt_channel.send(
            f"Welcome {mentions} to {group_name}! Your Atomic Team for the month! To get started: \n\n"
            "1. Introduce yourself! What are you working on right now? What would you like help with?"
            " What skills do you have that you can use to help others?\n\n"
            "2. Make an appointment to meet some time during the first week - get to know each other, determine how you best communicate with everyone in your team, and how often you want to check in (be sure to check in at least once a week).\n\n"
            "Need something to find a time for everyone? Try https://whenisgood.net/Create\n\n"
            "Thank you for participating and please share any feedback and sugestions in the #feedback-and-suggestions channel!"
        )


async def delete_on_demand_group(guild_id, channel):
    cat_id = GUILD_2_COLLAB_SESSION_CAT_ID.get(guild_id)
    if not cat_id:
        return
    channel_name = channel.name
    if not channel_name.startswith("session-") or not channel_name.endswith("-text"):
        return
    session_prefix = channel_name[:-5]
    category = client.get_channel(cat_id)
    for c in category.channels:
        if c.name == session_prefix + "-voice":
            await c.delete()
            break
    await channel.delete()


async def make_on_demand_group(guild, members, duration=30):
    if not members:
        return
    guild_id = guild.id
    # create permision overwide for text and voice channels using default permissions
    txt_channel_perm = discord.PermissionOverwrite(
        view_channel=True,
        **{key: value for key, value in discord.Permissions.text() if value},
    )
    voice_channel_perm = discord.PermissionOverwrite(
        view_channel=True,
        **{key: value for key, value in discord.Permissions.voice() if value},
    )
    random_name = get_random_name()
    group_name = f"session-{random_name}"
    cat_id = GUILD_2_COLLAB_SESSION_CAT_ID.get(guild_id)
    if not cat_id:
        return
    category = client.get_channel(cat_id)
    private_channel_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
    }
    txt_channel = await category.create_text_channel(
        group_name + "-text", overwrites=private_channel_perm
    )
    voice_channel = await category.create_voice_channel(
        group_name + "-voice", overwrites=private_channel_perm
    )
    for member in members:
        if member.id == POOKIE_USER_ID:
            continue
        try:
            await txt_channel.set_permissions(member, overwrite=txt_channel_perm)
            await voice_channel.set_permissions(member, overwrite=voice_channel_perm)
        except Exception as e:
            logger.exception(e)
    mentions = " ".join([x.mention for x in members if x.id != POOKIE_USER_ID])
    start_time = round(datetime.datetime.now().timestamp())
    session_id = hashlib.md5(f"discord-{guild_id}".encode("ascii")).hexdigest()
    await txt_channel.send(
        f"Thank you {mentions} for joining session {random_name}!\n\n - Say hi to each other. \n"
        f" - Share your goals for the next {duration} minutes.\n"
        " - Celebrate your wins together!\n\n"
        f'When you are done. Type "{client.user.mention} end session" to delete the session here!\n\n'
        "Here's the timer for this session. You can scan the QR Code to open it on your phone.\n"
        f"https://thinkdivergent.io/join-coworking/{session_id}-{start_time}-{duration}/\n"
    )


@client.event
async def on_ready():
    print("We have logged in as {0.user}".format(client))


@client.event
async def on_message(message):
    txt = message.content.lower()
    if message.author == client.user:
        if txt.startswith("a focus session is starting"):
            await message.add_reaction(EMOJI_CHECK_MARK)
            session_users = {}

            def check(reaction, user):
                if user == client.user:
                    return
                if str(reaction.emoji) == EMOJI_CHECK_MARK:
                    session_users[user.id] = user
                    if len(session_users) == 4:
                        return True
                return False

            try:
                await client.wait_for("reaction_add", timeout=300.0, check=check)
            except asyncio.TimeoutError:
                if len(session_users) > 1:
                    await message.channel.send(
                        f"{len(session_users)} people just joined a focus session!\n\n"
                        'Start your own with by typing "/start-session" into the chat!'
                    )
                    await make_on_demand_group(
                        message.guild, list(session_users.values())
                    )
                await message.delete()
            else:
                if len(session_users) > 1:
                    await message.channel.send(
                        f"{len(session_users)} people just joined a focus session!\n\n"
                        'Start your own with by typing "/start-session" into the chat!'
                    )
                    await make_on_demand_group(
                        message.guild, list(session_users.values())
                    )
                await message.delete()
        return
    if txt.startswith("</start-session"):
        try:
            await message.delete()
        except discord.errors.NotFound:
            # this is ok, a different bot(Pookie Dev for example) deleted it
            pass
        return
    # create focus sessions
    if message.content.startswith(f"<@!{POOKIE_USER_ID}> create session"):
        await make_on_demand_group(message.guild, message.mentions)
        return
    if message.content.startswith(f"<@!{POOKIE_USER_ID}> create focus session"):
        await make_on_demand_group(message.guild, message.mentions)
        return
    if message.content.startswith(f"<@!{POOKIE_USER_ID}> end session"):
        await delete_on_demand_group(message.guild.id, message.channel)
        return
    if message.guild.id != THINK_DIVERGENT_GUILD:
        return
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


@slash.slash(name="start-session", description="Start a focus session in 5 minutes")
async def _test(ctx: SlashContext):
    await ctx.respond()
    await ctx.send(
        content=f"A focus session is starting in 5 minutes! React with {EMOJI_CHECK_MARK} to join!",
    )
