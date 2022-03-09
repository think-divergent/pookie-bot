import requests
import pytz
import asyncio
import arrow
from collections import defaultdict
import os
import datetime
import random
import hashlib

from typing import Dict
import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext
from common_responses import SIMPLE_RESPONSES
import logging
from petname import get_random_name


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

intents = discord.Intents.default()
intents.members = True
intents.messages = True
intents.presences = True
client = commands.Bot(command_prefix="", intents=intents)
slash = SlashCommand(client)

COWORKING_SERVER_URL = os.environ.get("COWORKING_SERVER_URL", "http://localhost:5000")
EMOJI_CHECK_MARK = "✅"
POOKIE_USER_ID = os.environ.get("POOKIE_USER_ID", 795343874049703986)
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
}

GUILD_2_ONBOARDING_CAT_ID = {
    742405250731999273: 919013239755522071,
    699390284416417842: 919027765561393165,  # SS
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

with open("daily_topics.txt", "r") as f:
    daily_topics = f.read().split("\n")


def _daily_random_shuffle(items):
    rnd = random.Random()
    rnd.seed(int(datetime.datetime.now().timestamp() // (3600 * 24)))
    rnd.shuffle(items)


def group_participants(participants):
    # random participants
    participants = [x for x in participants]
    _daily_random_shuffle(participants)
    if len(participants) > 12:
        group_size = 4
    elif len(participants) == 8:
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


async def make_groups(request_channel=None, dry_run=False):
    """create groups"""
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
    member_id_to_members = {p.id: p for p in participants}
    # figure out who signed up for times
    availability_msg = await client.get_channel(ANNOUNCEMENT_CHANNEL_ID).fetch_message(
        TIME_MSG_ID
    )
    reactions = availability_msg.reactions
    groups_to_members = {}
    for rec in reactions:
        if rec.emoji in REACTION_TO_IDX:
            groups_to_members[REACTION_TO_IDX[rec.emoji]] = [
                m
                for m in await rec.users().flatten()
                # if m.id != STEVE_ID
            ]
    groups_to_member_ids = {}
    for group, members in groups_to_members.items():
        groups_to_member_ids[group] = set([x.id for x in members])
        member_id_to_members.update({m.id: m for m in members})
    all_members = [
        m
        for m in member_id_to_members.values()
        # if m.id != STEVE_ID
    ]
    groups = group_members_by_timeslot(all_members, groups_to_member_ids)
    if dry_run:
        if request_channel:
            output = "\n".join(
                [
                    f"Team {gid+1} ({GROUP_IDX_TO_MEET_TIME.get(gid, 'unknown')}) : "
                    + ", ".join([m.display_name for m in g])
                    for gid, g in groups.items()
                ]
            )
            await request_channel.send(output)
        return
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
    for idx, group in groups.items():
        group_name = f"team-{get_random_name()}"
        txt_channel = await category.create_text_channel(group_name + "-text")
        voice_channel = await category.create_voice_channel(group_name + "-voice")
        meet_time = GROUP_IDX_TO_MEET_TIME.get(idx, None)
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
        msg_header = (
            f"Welcome {mentions} to {group_name}! Your Atomic Team for the month! To get started: \n\n"
            "1. Introduce yourself! What are you working on these days? What would you like some help with?"
            " What do you enjoy helping others with?\n\n"
        )
        msg_body = (
            "2. Since you haven't picked your perferred weekly meet time (https://discord.com/channels/742405250731999273/811024435330678784/871734658931511367), make an appointment to meet some time during the first week - get to know each other, determine how you best communicate with everyone in your team, and how often you want to check in (be sure to check in at least once a week).\n\n"
            "Need something to find a time for everyone? Pick some times that work the best for you here! https://whenisgood.net/4a7nkn5/results/a9gkcir\n\n"
        )
        kwargs = {}
        if meet_time:
            now = arrow.now("US/Eastern")
            begin_of_week = now.floor("week")
            start_time = begin_of_week + datetime.timedelta(
                days=meet_time["date"] - 1,
                hours=meet_time["hour"],
                minutes=meet_time["minute"],
            )
            if start_time < now:
                start_time += datetime.timedelta(days=7)
            event_end_time = start_time + datetime.timedelta(hours=1)
            end_time = start_time
            end_time += datetime.timedelta(days=7 * 5)
            event_count = 6
            meet_time_str = start_time.format("dddd hh:mm a")
            start_time_str = start_time.format("YYYYMMDDTHHmmss")
            end_time_str = event_end_time.format("YYYYMMDDTHHmmss")
            calendar_url = f"https://calendar.google.com/calendar/u/0/r/eventedit?dates={start_time_str}/{end_time_str}&text=Think%20Divergent%20Atomic%20Team&location=Discord%20Voice%20Channel&recur=RRULE:FREQ%3DWEEKLY;COUNT%3D{event_count}&ctz=America%2FNew_York"
            msg_body = f"2. Looks like the best time for all of you to get together is weekly on {meet_time_str} US Eastern Time. You can add these times to your google calendar through this link: {calendar_url}. If this time doesn't work for you, no worries, feel free to still share updates through text with each other! \n\n"
        msg_footer = "Thank you for participating and please share any feedback and suggestions in the #feedback-and-suggestions channel!"
        await txt_channel.send(f"{msg_header}{msg_body}{msg_footer}", **kwargs)
        await txt_channel.send(
            "By the way, remember to enable notification for this channel so you won't miss any reminders here! https://imgur.com/a/au6fHwC"
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


def get_new_session_link():
    res = requests.post(f"{COWORKING_SERVER_URL}/internal/start-coworking-session/")
    if not res.ok:
        return None
    return res.json().get("url", None)


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
    # genreate a fallback url
    url = f"https://thinkdivergent.io/join-coworking/{session_id}-{start_time}-{duration}/\n"
    new_session_link = get_new_session_link()
    # if we can get a new session link use that session link
    if new_session_link:
        url = f"https://thinkdivergent.com{new_session_link}"
    await txt_channel.send(
        f"Thank you {mentions} for joining session {random_name}!\n\n - Say hi to each other. \n"
        f" - Share your goals for the next {duration} minutes.\n"
        " - Celebrate your wins together!\n\n"
        f'When you are done. Type "{client.user.mention} end session" to delete the session here!\n\n'
        "Here's the timer for this session. You can scan the QR Code to open it on your phone.\n"
        f"{url}"
    )


async def make_onboarding_group(guild, members):
    guild_id = guild.id
    # create permision overwide for text and voice channels using default permissions
    txt_channel_perm = discord.PermissionOverwrite(
        view_channel=True,
        **{key: value for key, value in discord.Permissions.text() if value},
    )
    random_name = get_random_name()
    group_name = f"{members[0]}-onboarding-group-{random_name}"
    cat_id = GUILD_2_ONBOARDING_CAT_ID.get(guild_id)
    if not cat_id:
        return
    category = client.get_channel(cat_id)
    private_channel_perm = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
    }
    txt_channel = await category.create_text_channel(
        group_name, overwrites=private_channel_perm
    )
    for member in members:
        try:
            await txt_channel.set_permissions(member, overwrite=txt_channel_perm)
        except Exception as e:
            logger.exception(e)
    await txt_channel.send(
        f"Hey {members[0].mention}, thanks for joining us! We’re so happy to have you as part of our community.\n\n"
        f"To help you find your way around and navigate our cultivated chaos, please meet your onboarding buddy {members[1].mention}. Go ahead and ask them any questions you might have about Think Divergent, what we have going on, or anything else that’s on your mind. \n\n"
        "Feeling adventurous? Here's an onboarding challenge for you:\n\n"
        "Find the person who's talked about crypto the most on this server and figure out their favorite coin right now!\n\n"
        "Feel free to team up with your buddy! Good luck and have fun! :orange_heart:"
    )


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


def group_members_by_timeslot(
    all_members, groups_to_member_ids: Dict[int, set], get_id=lambda x: x.id
):
    # deep copy groups to member_ids so we don't modify the original
    print(all_members)
    print(groups_to_member_ids)
    groups_to_member_ids = {
        group: {mid for mid in member_ids}
        for group, member_ids in groups_to_member_ids.items()
    }
    member_id_to_member = {get_id(m): m for m in all_members}
    member_ids_to_groups = defaultdict(list)
    groups_to_delete = []
    for group_idx, uids in groups_to_member_ids.items():
        if len(uids) > 1:
            for u in uids:
                member_ids_to_groups[u].append(group_idx)
        else:
            groups_to_delete.append(group_idx)

    # eliminate invalid groups with just one member
    for group_idx in groups_to_delete:
        groups_to_member_ids.pop(group_idx, None)

    member_group_assignment = {}
    group_member_assignments = defaultdict(set)

    members_to_resolve = set(member_ids_to_groups.keys())

    # keep track of if this outerloop makes a change
    resolved_constraint = True
    while resolved_constraint:
        resolved_constraint = False
        for member_id in members_to_resolve:
            groups = member_ids_to_groups[member_id]
            # if member is the only person in a group
            if len(groups) == 1:
                group_idx = groups[0]
                logger.debug(f"Found {member_id} with only one option {group_idx}")
                member_group_assignment[member_id] = group_idx  # assign member to group
                group_member_assignments[group_idx].add(
                    member_id
                )  # assign group to member
                groups_to_member_ids[group_idx].remove(
                    member_id
                )  # remove user from current group
                members_to_resolve.remove(member_id)  # remove frommembers to resolve
                logger.debug(f"{member_id} allocated to {group_idx}")
                # if group only has one other member available, allocate the other member
                if len(group_member_assignments[group_idx]) == 1:
                    if len(groups_to_member_ids[group_idx]) == 1:
                        other_member_id = next(iter(groups_to_member_ids[group_idx]))
                        member_group_assignment[
                            other_member_id
                        ] = group_idx  # assign member to group
                        group_member_assignments[group_idx].add(
                            other_member_id
                        )  # assign group to member
                        # remove other user from all of their groups
                        for other_group in member_ids_to_groups[other_member_id]:
                            groups_to_member_ids[other_group].remove(other_member_id)
                        # remove from members to resolve
                        members_to_resolve.remove(other_member_id)
                        logger.debug(f"{other_member_id} allocated to {group_idx}")
                    elif len(groups_to_member_ids[group_idx]) == 0:
                        logger.debug(
                            f"{member_id} in {group_idx} can not be paired with anyone"
                        )
                resolved_constraint = True
                break

    # for each left over member, put them into groups, fill the smallest groups first
    for member_id in members_to_resolve:
        viable_groups = [
            x
            for x in member_ids_to_groups[member_id]
            if len(group_member_assignments[x])
        ]
        # TODO use a heap
        sorted_viable_groups = sorted(
            viable_groups,
            key=lambda x: (len(group_member_assignments[x]), x),
        )
        group_idx = sorted_viable_groups[0]
        member_group_assignment[member_id] = group_idx  # assign member to group
        group_member_assignments[group_idx].add(member_id)  # assign group to member
        # remove user from all of their groups
        for other_group in member_ids_to_groups[member_id]:
            groups_to_member_ids[other_group].remove(member_id)
        logger.debug(f"{member_id} allocated to {group_idx}")

    # for all of the other members who don't have preferences set, assign them to groups randomly
    members_to_assign = sorted(
        [get_id(m) for m in all_members if get_id(m) not in member_group_assignment]
    )
    # non empty groups
    viable_groups = [
        x for x in group_member_assignments.keys() if len(group_member_assignments[x])
    ]
    _daily_random_shuffle(members_to_assign)
    last_added = None
    for member_id in members_to_assign:
        # put into groups with lowest member count
        # TODO use a heap
        if viable_groups:
            sorted_viable_groups = sorted(
                viable_groups,
                key=lambda x: (len(group_member_assignments[x]), x),
            )
            group_idx = sorted_viable_groups[0]
        else:
            group_idx = -1
        if len(group_member_assignments[group_idx]) == 4:
            # the smallest groups have 4 people already break the rest to random groups
            group_idx = -1
        member_group_assignment[member_id] = group_idx  # assign member to group
        group_member_assignments[group_idx].add(member_id)  # assign group to member
        last_added = member_id

    # if overflow group has only one person
    if len(group_member_assignments[-1]) == 1:
        member_id = group_member_assignments[-1]
        if last_added is not None:
            # move the last added person to this group
            # there are overflow people
            # remove last added member and add them to this group
            last_group_id = member_group_assignment[last_added]
            group_member_assignments[last_group_id].remove(last_added)
            member_group_assignment[last_added] = -1  # assign member to group
            group_member_assignments[-1].add(last_added)  # assign group to member
        else:
            # add this person to group 0, everyone else is filled based on availability
            group_idx = 0
            member_group_assignment[member_id] = group_idx  # assign member to group
            group_member_assignments[group_idx].add(member_id)  # assign group to member
    elif (
        len(group_member_assignments[-1]) > 1
    ):  # if overflow group has more than one person
        overflow_groups = group_participants(sorted(group_member_assignments[-1]))
        for i in range(len(overflow_groups)):
            group_member_assignments[-i - 1] = overflow_groups[i]
    final_groups = {}
    for group_idx, member_ids in group_member_assignments.items():
        if len(member_ids):
            members = [member_id_to_member[m] for m in sorted(member_ids)]
            final_groups[group_idx] = members
    return final_groups


@client.event
async def on_message(message):
    txt = message.content.lower()
    if message.author == client.user:
        if txt.startswith("a focus session is starting"):
            print("new session starting")
            await message.add_reaction(EMOJI_CHECK_MARK)
            session_users = {}

            def check(reaction, user):
                if user == client.user:
                    return
                if str(reaction.emoji) == EMOJI_CHECK_MARK:
                    session_users[user.id] = user
                    if len(session_users) == 2:
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
    if txt == "test_groups" and message.guild.id == 699390284416417842:
        await make_groups(request_channel=message.channel, dry_run=True)
        return
    if message.guild.id != THINK_DIVERGENT_GUILD:
        return
    if txt == "create_groups":
        print("got create_groups")
        if message.author.id != STEVE_ID:
            return
        print("Creating Groups")
        await make_groups()
        print("Created Groups")
        return
    if txt == "dry_run_create_groups":
        print("got create_groups")
        if message.author.id != STEVE_ID:
            return
        print("Creating Groups")
        await make_groups(request_channel=message.channel, dry_run=True)
        print("Created Groups")
        return
    for prompt, responses in SIMPLE_RESPONSES.items():
        if txt.startswith(prompt):
            await message.channel.send(random.choice(responses))
            return


@slash.slash(name="start-session", description="Start a focus session in 5 minutes")
async def _test(ctx: SlashContext):
    await ctx.send(content="Ok! React below to join 👇", hidden=True)
    await ctx.channel.send(
        content=f"A focus session is starting in 5 minutes! React with {EMOJI_CHECK_MARK} to join!",
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
                await channel.send(random_topic)
