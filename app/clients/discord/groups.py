import itertools
import urllib
import arrow
import random
import os
import requests
import hashlib
import datetime
import logging
import discord
from petname import get_random_name
from server_config import get_discord_server_config
from clients.discord.client import client, POOKIE_USER_ID
from clients.discord.consts import EMOJI_CHECK_MARK

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

COWORKING_SERVER_URL = os.environ.get("COWORKING_SERVER_URL", "http://localhost:5000")


def get_new_session_link(slug=None):
    res = requests.post(f"{COWORKING_SERVER_URL}/internal/start-coworking-session/", json={
        'slug': slug
    })
    if not res.ok:
        return None
    return res.json().get("url", None)


def get_connect_account_token(user):
    if not user:
        return None
    payload = {
        "platform": "discord",
        "account_id": str(user.id),
        "extras": {"username": user.name, "display_name": user.display_name},
    }
    res = requests.post(
        f"{COWORKING_SERVER_URL}/internal/connect-account-token/",
        json=payload,
    )
    if not res.ok:
        return None
    return res.json().get("token", None)


def get_atomic_team_groups_for_participants(guild_id, participant_ids):
    server_config = get_discord_server_config(guild_id)
    payload = {
        "platform": "discord",
        "server_id": str(guild_id),
        "participant_ids": [str(pid) for pid in participant_ids],
    }
    if server_config and server_config.get("alliance_slug"):
        payload["alliance_slug"] = server_config.get("alliance_slug")
    res = requests.post(
        f"{COWORKING_SERVER_URL}/internal/atomic-team-groups/",
        json=payload,
    )
    if not res.ok:
        return None
    return res.json()


def _daily_random_shuffle(items):
    rnd = random.Random()
    rnd.seed(int(datetime.datetime.now().timestamp() // (3600 * 24)))
    rnd.shuffle(items)


async def make_on_demand_group(guild, members, duration=30):
    if not members or not guild or not guild.id:
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
    guild_config = get_discord_server_config(guild_id)
    if not guild_config or not guild_config.get("coworking_category"):
        return
    cat_id = guild_config.get("coworking_category")
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
    slug = guild_config.get('alliance_slug', None)
    # genreate a fallback url
    if slug:
        url = f"https://thinkdivergent.io/join-coworking/{slug}/{session_id}-{start_time}-{duration}/\n"
    else:
        url = f"https://thinkdivergent.io/join-coworking/{session_id}-{start_time}-{duration}/\n"
    new_session_link = get_new_session_link(slug=slug)
    # if we can get a new session link use that session link
    if new_session_link:
        url = f"https://thinkdivergent.com{new_session_link}"
    await txt_channel.send(
        f"Thank you {mentions} for joining session {random_name}!\n\n - Say hi to each other. \n"
        f" - Share your goals for the next {duration} minutes.\n"
        " - Celebrate your wins together!\n\n"
        f'When you are done. Type "<@{POOKIE_USER_ID}> end session" to delete the session here!\n\n'
        "Here's the timer for this session. You can scan the QR Code to open it on your phone.\n"
        f"{url}"
    )


async def make_onboarding_group(guild, members):
    guild_id = guild.id
    guild_config = get_discord_server_config(guild_id)
    if not guild_config or not guild_config.get("onboarding_category"):
        return
    cat_id = guild_config.get("onboarding_category")
    # create permision overwide for text and voice channels using default permissions
    txt_channel_perm = discord.PermissionOverwrite(
        view_channel=True,
        **{key: value for key, value in discord.Permissions.text() if value},
    )
    group_name = f"👋{members[0].display_name}"
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
    msg = (
        f"Welcome to the {guild.name} community {members[0].mention}!\n\n"
        f"Meet your onboarding buddy {members[1].mention}!\n"
        f"Feel free to ask them any questions you might have about the community,\n"
        f"what we have going on, how you can contribute, and etc. \n\n"
    )
    if guild_config and guild_config.get("onboarding_challenge"):
        onboarding_challenge = guild_config.get("onboarding_challenge")
        msg += (
            "Feeling adventurous? Here's an onboarding challenge:\n"
            f"{onboarding_challenge}\nTeam up with your buddy and enjoy the community!"
        )
    await txt_channel.send(msg)


async def delete_on_demand_group(guild_id, channel):
    guild_config = get_discord_server_config(guild_id)
    if not guild_config or not guild_config.get("coworking_category"):
        return
    cat_id = guild_config.get("coworking_category")
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


async def delete_archived_atomic_teams(guild_id):
    guild_config = get_discord_server_config(guild_id)
    if not guild_config or not guild_config.get("archived_atomic_team_category"):
        return
    old_teams_category_id = guild_config.get("archived_atomic_team_category")
    # move channels to archive if necessary
    archive_category = client.get_channel(old_teams_category_id)
    for channel in archive_category.channels:
        await channel.delete()


async def make_atomic_teams(guild_id, dry_run_channel=None, guild=None):
    """create groups"""
    print("Creating groups...")
    guild_config = get_discord_server_config(guild_id)
    if not guild_config:
        return
    opt_in_channel_id = guild_config.get("atomic_team_signup_channel_id")
    opt_in_msg_id = guild_config.get("atomic_team_signup_msg_id")
    teams_category_id = guild_config.get("atomic_team_category")
    old_teams_category_id = guild_config.get("archived_atomic_team_category")
    default_meet_time = guild_config.get("default_atomic_team_time")
    if not opt_in_channel_id or not opt_in_msg_id or not teams_category_id:
        return
    channel = client.get_channel(opt_in_channel_id)
    msg = await channel.fetch_message(opt_in_msg_id)
    reaction = None
    for rec in msg.reactions:
        if rec.emoji == EMOJI_CHECK_MARK:
            reaction = rec
            break
    if not reaction:
        return
    participants = await reaction.users().flatten()
    groups = get_atomic_team_groups_for_participants(
        guild_id, [x.id for x in participants]
    )
    if not groups:
        return
    all_participants = [t["members"] for t in groups["teams"]]
    all_participants = set(itertools.chain(*all_participants))
    unknown_participants = all_participants - set([str(p.id) for p in participants])
    if guild:
        extra_participants = [
            guild.get_member(int(x))
            for x in unknown_participants
            if guild.get_member(int(x))
        ]
        participants = participants + extra_participants
    group_to_meet_time = groups.get("timeslots", {})
    meet_time_tz = groups.get("tz", "America/New_York")
    member_id_to_member = {str(x.id): x for x in participants}
    output = "\n".join(
        [
            f"Team {idx} ({group_to_meet_time.get(team['timeslot'], 'unknown')}) : "
            + ", ".join(
                [
                    member_id_to_member[mid].display_name
                    for mid in team["members"]
                    if mid in member_id_to_member
                ]
            )
            for idx, team in enumerate(groups.get("teams"))
        ]
    )
    if dry_run_channel:
        await dry_run_channel.send(output)
        return
    category = client.get_channel(teams_category_id)
    if old_teams_category_id:
        # move channels to archive if necessary
        archive_category = client.get_channel(old_teams_category_id)
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
    for idx, group in enumerate(groups["teams"]):
        group_name = f"team-{get_random_name()}"
        txt_channel = await category.create_text_channel(group_name + "-text")
        voice_channel = await category.create_voice_channel(group_name + "-voice")
        meet_time = group_to_meet_time.get(group["timeslot"], default_meet_time)
        for participant in group["members"]:
            if participant not in member_id_to_member:
                continue
            try:
                await txt_channel.set_permissions(
                    member_id_to_member[participant], overwrite=txt_channel_perm
                )
                await voice_channel.set_permissions(
                    member_id_to_member[participant], overwrite=voice_channel_perm
                )
            except Exception as e:
                logger.exception(e)
        mentions = " ".join(
            member_id_to_member[x].mention
            for x in group["members"]
            if x in member_id_to_member
        )
        msg_header = (
            f"Welcome {mentions} to your Atomic Team for the next 4 weeks. To get started: \n\n"
            "1. Introduce yourself!\n- What are you working on these days?\n- What do you love about what you do?\n- What could you use some help with?"
            "\n- What do you enjoy helping others with?\n🎁 Mystery prize for the first person to make the intro!\n\n"
        )
        msg_body = (
            "2. Since you haven't picked your perferred weekly meet time (https://discord.com/channels/742405250731999273/811024435330678784/871734658931511367), make an appointment to meet some time during the first week - get to know each other, determine how you best communicate with everyone in your team, and how often you want to check in (be sure to check in at least once a week).\n\n"
            "Need something to find a time for everyone? Pick some times that work the best for you here! https://whenisgood.net/4a7nkn5/results/a9gkcir\n\n"
        )
        kwargs = {}
        if meet_time:
            now = arrow.now(meet_time_tz)
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
            event_count = 4
            meet_time_str = start_time.format("dddd hh:mm a")
            start_time_str = start_time.format("YYYYMMDDTHHmmss")
            end_time_str = event_end_time.format("YYYYMMDDTHHmmss")
            calendar_url = f"https://calendar.google.com/calendar/u/0/r/eventedit?dates={start_time_str}/{end_time_str}&text=Think%20Divergent%20Atomic%20Team&location=Discord%20Voice%20Channel&recur=RRULE:FREQ%3DWEEKLY;COUNT%3D{event_count}&ctz={urllib.parse.quote_plus(meet_time_tz)}"
            msg_body = f"2. Looks like the best time for all of you to get together is weekly on {meet_time_str} US Eastern Time.\nYou can add these times to your google calendar with the link below.\nIf this time doesn't work for you, no worries, feel free to still share updates through text with each other! \n\n"
            kwargs["embed"] = discord.Embed(
                title="Add to Google Calendar",
                description="Add your team's meet times to your google calendar with this link",
                url=calendar_url,
            )
        msg_footer = ""
        await txt_channel.send(f"{msg_header}{msg_body}{msg_footer}", **kwargs)
        await txt_channel.send(
            "By the way, remember to enable notification for this channel so you won't miss any reminders here! https://imgur.com/a/au6fHwC"
        )


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
