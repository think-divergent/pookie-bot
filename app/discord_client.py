import json
import time
import pytz
import asyncio
import os
import datetime
import random

import discord
from discord.ext import tasks
from discord_slash import SlashContext
from common_responses import SIMPLE_RESPONSES
import logging
import redis
from server_config import get_discord_server_config
from clients.discord.client import client, POOKIE_USER_ID, slash
from clients.discord.consts import EMOJI_CHECK_MARK
from clients.discord.groups import get_connect_account_token
from clients.discord.groups import (
    make_atomic_teams,
    make_onboarding_group,
    make_on_demand_group,
    delete_on_demand_group,
    delete_archived_atomic_teams,
)


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

REDIS_URL = os.environ.get("REDIS_URL", "redis://0.0.0.0/0")
LANDING_PAD_CHANNEL_ID = 792039815327645736
SIGNUP_MSG_ID = 812836894013915176
ANNOUNCEMENT_CHANNEL_ID = 811024435330678784
TIME_MSG_ID = 871734658931511367
ATOMIC_TEAM_CATEGORY_ID = 812829505013809182
OLD_ATOMIC_TEAM_CATEGORY_ID = 812862635333648435
STEVE_ID = 209669511517962241
THINK_DIVERGENT_GUILD = 742405250731999273
if os.getenv("DEVPOOKIE"):
    # landing page and time sign up on dev server
    LANDING_PAD_CHANNEL_ID = 874091378555117630
    SIGNUP_MSG_ID = 874091395143585844
    ANNOUNCEMENT_CHANNEL_ID = 874091683980140585
    TIME_MSG_ID = 874091842478686288
    ATOMIC_TEAM_CATEGORY_ID = 874096677487792158
    OLD_ATOMIC_TEAM_CATEGORY_ID = 874096726707957770
    THINK_DIVERGENT_GUILD = 699390284416417842
EXISTING_PARTICIPANTS_SET = set()
EXISTING_PARTICIPANTS = []

# TODO save this to DB somewhere
GUILD_2_COLLAB_SESSION_CAT_ID = {
    806941792532168735: 810096286492655646,  # ASI
    699390284416417842: 815777518699020318,  # SS
    742405250731999273: 897800785423917056,  # TD
    968468250495160330: 968511008840777838,  # WID
}

GUILD_2_ONBOARDING_CAT_ID = {
    742405250731999273: 919013239755522071,
    699390284416417842: 919027765561393165,  # SS
    968468250495160330: 968511381378859068,  # WID
}

REACTION_TO_IDX = {
    "1️⃣": 0,
    "2️⃣": 1,
    "3️⃣": 2,
    "4️⃣": 3,
    "5️⃣": 4,
    "6️⃣": 5,
}

GROUP_IDX_TO_MEET_TIME = {
    0: {
        "date": 1,
        "hour": 10,
        "minute": 30,
    },
    1: {
        "date": 3,
        "hour": 14,
        "minute": 30,
    },
    2: {
        "date": 3,
        "hour": 19,
        "minute": 30,
    },
    3: {
        "date": 2,
        "hour": 11,
        "minute": 30,
    },
}

# test redis connection first
redis_service = redis.Redis.from_url(REDIS_URL)
connected = False
for i in range(5):
    try:
        redis_service.ping()
        connected = True
        break
    except redis.exceptions.ConnectionError as e:
        logger.error("Failed to connect to redis. Retrying in 1 sec...")
        logger.exception(e)
        time.sleep(1)
if not connected:
    logger.error("Giving up on connecting to redis")
    raise redis.exceptions.ConnectionError(f"Failed to connect to redis at {REDIS_URL}")

with open("daily_topics.txt", "r") as f:
    # remove lines with just whitespaces
    daily_topics = [x for x in f.read().split("\n") if x.strip()]


@client.event
async def on_ready():
    print("we have logged in as {0.user}".format(client))


@client.event
async def on_member_join(member):
    roles = member.guild.roles
    onboarding_buddy_roles = [r for r in roles if r.name == "Onboarding Buddy"]
    if not onboarding_buddy_roles:
        return
    onboarding_buddy_role = onboarding_buddy_roles[0]
    buddies = onboarding_buddy_role.members
    if not buddies:
        return
    online_buddies = [b for b in buddies if b.status == discord.Status.online]
    pool = online_buddies if online_buddies else buddies
    buddy = random.choice(pool)
    await make_onboarding_group(member.guild, [member, buddy])


@client.event
async def on_raw_reaction_add(reaction):
    # check for atomic team sign up message
    guild_config = get_discord_server_config(reaction.guild_id)
    if (
        not guild_config
        or "alliance_slug" not in guild_config
        or reaction.message_id != guild_config.get("atomic_team_signup_msg_id")
        or reaction.channel_id != guild_config.get("atomic_team_signup_channel_id")
        or reaction.emoji.name != EMOJI_CHECK_MARK
    ):
        return
    guild = client.get_guild(reaction.guild_id)
    if not guild:
        return
    # new member signed up for atomic team
    token = get_connect_account_token(reaction.member)
    slug = guild_config["alliance_slug"]
    url = f"https://thinkdivergent.com/a/{slug}/atomic-teams/availability/{token}"
    await reaction.member.send(
        f"Welcome to Atomic Teams at {guild.name.capitalize()}!\nSet your availability for a weekly meet up with your team with the link below\n{url}",
        embed=discord.Embed(
            type="video",
            title=f"Set availability for Atomic Teams at {guild.name.capitalize()}",
            description="Set and update your availability to meet weekly with your atomic team.",
            url=url,
        ).set_image(url="https://cdn.thinkdivergent.com/video/set-availability.gif"),
    )


async def get_random_topic_for_channel(channel):
    messages = set([m.content for m in await channel.history(limit=90).flatten()])
    new_topics = [x for x in daily_topics if x.strip() not in messages]
    if new_topics:
        return random.choice(new_topics)
    else:
        return random.choice(daily_topics)


@client.event
async def on_message(message):
    txt = message.content.lower()
    if message.author == client.user:
        if txt.startswith("a coworking session is starting"):
            session_users = {}
            if message.embeds:
                timestamp = message.embeds[0].timestamp.timestamp()
                interaction_key = (
                    f"pookie|session_starter|{message.channel.id}_{timestamp}"
                )
                starter_id = int(redis_service.get(interaction_key))
                member = message.guild.get_member(starter_id)
                session_users[member.id] = member
            print("new session starting")
            await message.add_reaction(EMOJI_CHECK_MARK)

            session_ready_time = {"current": None}

            def check(reaction, user):
                if user == client.user:
                    return
                if str(reaction.emoji) == EMOJI_CHECK_MARK:
                    session_users[user.id] = user
                    if len(session_users) == 2:
                        session_ready_time["current"] = datetime.datetime.utcnow()
                    if len(session_users) >= 2:
                        return True
                return False

            check_frequency = 15
            for i in range(int(300 / check_frequency)):
                try:
                    await client.wait_for(
                        "reaction_add", timeout=check_frequency, check=check
                    )
                except asyncio.TimeoutError:
                    pass
                finally:
                    # if not last check, then wait another period for more users to join
                    if i * check_frequency + check_frequency < 300:
                        if not session_ready_time["current"]:
                            continue
                        if (
                            datetime.datetime.utcnow() - session_ready_time["current"]
                        ).total_seconds() < check_frequency - 1:
                            continue
                    if len(session_users) > 1:
                        await message.channel.send(
                            f"{len(session_users)} people just joined a coworking session!\n\n"
                            'Start your own with by typing "/start-session" into the chat!'
                        )
                        await make_on_demand_group(
                            message.guild, list(session_users.values())
                        )
                    await message.delete()
                    break
        return
    if txt.startswith("</start-session"):
        try:
            await message.delete()
        except discord.errors.NotFound:
            # this is ok, a different bot(Pookie Dev for example) deleted it
            pass
        return
    # create coworking sessions
    if f"{POOKIE_USER_ID}> create session" in message.content:
        await make_on_demand_group(message.guild, message.mentions)
        return
    if f"{POOKIE_USER_ID}> generate server config" in message.content:
        guild = message.guild
        config = {
            "alliance_slug": "############",
            "default_atomic_team_time": {
                "date": 3,
                "hour": 14,
                "minute": 30,
            },
        }
        for channel in guild.channels:
            if channel.name.lower() == "coworking":
                config["coworking_category"] = channel.id
            elif channel.name.lower() == "atomic teams":
                config["atomic_team_category"] = channel.id
            elif channel.name.lower() == "archived atomic teams":
                config["archived_atomic_team_category"] = channel.id
            elif channel.name.lower() == "onboarding":
                config["onboarding_category"] = channel.id
            elif channel.name.lower() == "start-here":
                config["atomic_team_signup_channel_id"] = channel.id
                signup_message = None
                for msg in await channel.history(limit=200).flatten():
                    if "atomic teams" in msg.content.lower():
                        signup_message = msg
                if not signup_message:
                    signup_message = await channel.send(
                        f"Welcome to {guild.name}. \nReact below to sign up for Atomic Teams."
                    )
                    await signup_message.add_reaction(EMOJI_CHECK_MARK)
                config["atomic_team_signup_msg_id"] = signup_message.id
        await message.channel.send(json.dumps(config, indent=4, sort_keys=True))
        return
    if f"{POOKIE_USER_ID}> create coworking session" in message.content:
        await make_on_demand_group(message.guild, message.mentions)
        return
    if f"{POOKIE_USER_ID}> end session" in message.content:
        await delete_on_demand_group(message.guild.id, message.channel)
        return
    if txt == "test_groups" and message.guild.id == 699390284416417842:
        await make_atomic_teams(
            message.guild.id, dry_run_channel=message.channel, guild=message.guild
        )
        return
    if f"{POOKIE_USER_ID}> create atomic teams" in txt:
        print("Creating Groups")
        await make_atomic_teams(message.guild.id, guild=message.guild)
        print("Created Groups")
        return
    if f"{POOKIE_USER_ID}> who is " in txt:
        uid = txt.split(" ")[-1]
        user = await client.fetch_user(int(uid))
        await message.channel.send(user.name)
        return
    if f"{POOKIE_USER_ID}> random topic" in txt:
        random_topic = await get_random_topic_for_channel(message.channel)
        await message.channel.send(random_topic)
        return
    if f"{POOKIE_USER_ID}> delete atomic teams" in txt:
        if not message.author.guild_permissions.administrator:
            return
        await delete_archived_atomic_teams(message.guild.id)
    if not message.guild or message.guild.id != THINK_DIVERGENT_GUILD:
        return
    if txt == "dry_run_create_groups":
        print("got create_groups")
        if message.author.id != STEVE_ID:
            return
        print("Creating Groups")
        await make_atomic_teams(
            message.guild.id, dry_run_channel=message.channel, guild=message.guild
        )
        print("Created Groups")
        return
    for prompt, responses in SIMPLE_RESPONSES.items():
        if txt.startswith(prompt):
            await message.channel.send(random.choice(responses))
            return


@slash.slash(name="start-session", description="Start a coworking session in 5 minutes")
async def _test(ctx: SlashContext):
    await ctx.send(content="Ok! Starting a session now!", hidden=True)
    # keep track of who started the session so they don't have to react to the message
    timestamp = datetime.datetime.utcnow()
    interaction_key = f"pookie|session_starter|{ctx.channel.id}_{timestamp.timestamp()}"
    interaction_value = ctx.author.id
    res = redis_service.set(interaction_key, interaction_value, ex=450)
    if not res:
        await ctx.channel.send(
            content="Something went wrong on our side. Please try again later",
        )
    await ctx.channel.send(
        content=f"A coworking session is starting in 5 minutes! \nReact with {EMOJI_CHECK_MARK} to join!",
        embed=discord.Embed(description="New coworking session", timestamp=timestamp),
    )


@slash.slash(
    name="update-availability", description="Update your availability for Atomic Teams"
)
async def slash_update_availability(ctx: SlashContext):
    # check for atomic team sign up message
    guild_config = get_discord_server_config(ctx.guild_id)
    if not guild_config:
        return
    guild = ctx.guild
    if not guild:
        return
    # new member signed up for atomic team
    token = get_connect_account_token(ctx.author)
    slug = guild_config["alliance_slug"]
    url = f"https://thinkdivergent.com/a/{slug}/atomic-teams/availability/{token}"
    embed = discord.Embed(
        title=f"Set availability for Atomic Teams at {guild.name.capitalize()}",
        description="Set and update your availability to meet weekly with your atomic team.",
        url=url,
    ).set_image(url="https://cdn.thinkdivergent.com/video/set-availability.gif")

    await ctx.send(
        content=f"Here's your link to update availability! {url}",
        embed=embed,
        hidden=True,
    )


shared_data = {
    "last_random_topic": datetime.datetime.now(pytz.timezone("America/New_York"))
}


@tasks.loop(seconds=50)
async def hourly_tasks():
    now = datetime.datetime.now(pytz.timezone("America/New_York"))
    if (
        now.hour != 8
        or now.minute != 30
        or (now - shared_data["last_random_topic"]).total_seconds() < 60
    ):
        return
    shared_data["last_random_topic"] = now
    td_guild = client.get_guild(THINK_DIVERGENT_GUILD)
    random_topic = random.choice(daily_topics)

    if td_guild:
        for channel in td_guild.channels:
            if channel.id == 951101588729126993:
                random_topic = await get_random_topic_for_channel(channel)
                await channel.send(random_topic)
