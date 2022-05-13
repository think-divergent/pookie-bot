import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from unittest import TestCase
from clients.discord.groups import (
    make_onboarding_group,
    make_on_demand_group,
    make_atomic_teams,
    delete_on_demand_group,
)
from clients.discord.consts import EMOJI_CHECK_MARK
import discord


def mock_connection_state():
    return discord.state.ConnectionState(
        dispatch=None, handlers=None, hooks=None, syncer=None, http=None, loop=None
    )


def mock_user(uid, guild, roles=[]):
    return discord.Member(
        data={
            "user": {
                "id": uid,
                "username": f"test_{uid}",
                "discriminator": "dtest",
                "avatar": "url",
            },
            "roles": [],
        },
        guild=guild,
        state=mock_connection_state(),
    )


class TestDiscord(TestCase):
    @patch("clients.discord.groups.get_new_session_link")
    @patch("clients.discord.groups.client.get_channel")
    @patch("clients.discord.groups.get_discord_server_config")
    def test_make_ondemand_groups(self, get_config, get_channel, get_new_session_link):
        guild = discord.Guild(
            data={"id": 1, "name": "test"}, state=mock_connection_state()
        )
        members = [mock_user(x, guild) for x in range(10)]
        get_config.return_value = {
            "coworking_category": 3,
        }
        get_new_session_link.return_value = "/testurl"
        mocked_category = AsyncMock()
        get_channel.return_value = mocked_category
        txt_channel = AsyncMock()
        voice_channel = AsyncMock()
        mocked_category.create_text_channel.return_value = txt_channel
        mocked_category.create_voice_channel.return_value = voice_channel
        asyncio.run(make_on_demand_group(guild, members, 30))
        sent_msg = txt_channel.send.call_args[0][0]
        self.assertTrue(len(sent_msg) > 300)
        self.assertEqual(sent_msg.count("<@"), 11)  # 10 members + 1 bot
        self.assertEqual(
            txt_channel.set_permissions.call_count, 10
        )  # grant permissions to all members
        self.assertEqual(
            voice_channel.set_permissions.call_count, 10
        )  # grant permissions to all members

    @patch("clients.discord.groups.client.get_channel")
    @patch("clients.discord.groups.get_discord_server_config")
    def test_make_onboarding_group(self, get_config, get_channel):
        guild = discord.Guild(
            data={"id": 1, "name": "test"}, state=mock_connection_state()
        )
        members = [mock_user(x, guild) for x in range(2)]
        get_config.return_value = {
            "onboarding_category": 5,
        }
        mocked_category = AsyncMock(spec_set=["create_text_channel"])
        get_channel.return_value = mocked_category
        txt_channel = AsyncMock()
        mocked_category.create_text_channel = AsyncMock(return_value=txt_channel)
        asyncio.run(make_onboarding_group(guild, members))
        sent_msg = txt_channel.send.call_args[0][0]
        self.assertEqual(sent_msg.count("<@0>"), 1)  # mention user
        self.assertEqual(sent_msg.count("<@1>"), 1)  # mention buddy
        self.assertTrue("challenge" not in sent_msg.lower())  # mention buddy
        self.assertEqual(
            txt_channel.set_permissions.call_count, 2
        )  # grant permissions to all members
        # with onboarding challenge
        challenge = "Pet a fox"
        get_config.return_value = {
            "onboarding_category": 5,
            "onboarding_challenge": challenge,
        }
        txt_channel.reset_mock()
        asyncio.run(make_onboarding_group(guild, members))
        sent_msg = txt_channel.send.call_args[0][0]
        self.assertTrue(len(sent_msg) > 300)
        self.assertEqual(sent_msg.count("<@"), 2)  # 2 members
        self.assertEqual(
            txt_channel.set_permissions.call_count, 2
        )  # grant permissions to all members
        self.assertTrue(challenge.lower() in sent_msg.lower())  # mention buddy

    @patch("clients.discord.groups.client.get_channel")
    @patch("clients.discord.groups.get_discord_server_config")
    def test_delete_ondemand_group(self, get_config, get_channel):
        get_config.return_value = {
            "coworking_category": 5,
        }
        mocked_category = AsyncMock(spec_set=["channels"])
        channel_1 = AsyncMock()
        channel_1.name = "session-test-text"
        channel_2 = AsyncMock()
        channel_2.name = "session-test-voice"
        channel_3 = AsyncMock()
        channel_3.name = "session-test2-voice"
        mocked_category.channels = [channel_1, channel_2, channel_3]
        get_channel.return_value = mocked_category
        guild_id = 1
        asyncio.run(delete_on_demand_group(guild_id, channel_1))
        channel_1.delete.assert_called_once()
        channel_2.delete.assert_called_once()
        self.assertEqual(channel_3.delete.call_count, 0)

    @patch("clients.discord.groups.get_atomic_team_groups_for_participants")
    @patch("clients.discord.groups.client.get_channel")
    @patch("clients.discord.groups.get_discord_server_config")
    def test_make_atomic_team(self, get_config, get_channel, get_groups):
        guild_id = 1
        get_groups.return_value = {
            "teams": [
                {"members": ["1", "2", "A"], "timeslot": "-1"},
                {"members": ["5", "6", "7", "8"], "timeslot": "20"},
                {"members": ["3", "4", "9", "0"], "timeslot": "24"},
            ],
            "timeslots": {
                "20": {"date": 1, "hour": 6, "minute": 0},
                "24": {"date": 1, "hour": 8, "minute": 0},
            },
            "tz": "America/New_York",
            "tzOffset": 240,
        }
        get_config.return_value = {
            "atomic_team_signup_channel_id": 3,
            "atomic_team_signup_msg_id": 5,
            "atomic_team_category": 7,
            "archived_atomic_team_category": 9,
        }
        # get opt in channel
        opt_in_category = AsyncMock(spec_set=["fetch_message"])
        teams_category = AsyncMock(
            spec_set=["channels", "create_text_channel", "create_voice_channel"]
        )
        archive_category = AsyncMock(spec_set=["fetch_message"])

        def get_category_for_id(cid):
            return {
                3: opt_in_category,
                7: teams_category,
                9: archive_category,
            }[cid]

        get_channel.side_effect = get_category_for_id
        # get opt in message
        opt_in_msg = AsyncMock(spec_set=["reactions"])
        opt_in_category.fetch_message = AsyncMock(return_value=opt_in_msg)
        # get message reactions
        checkmark_reaction = MagicMock(emoji=EMOJI_CHECK_MARK)
        opt_in_msg.reactions = [MagicMock(emoji="🚀"), checkmark_reaction]
        # get users reacted
        checkmark_users = MagicMock(spec_set=["flatten"])
        checkmark_users.flatten = AsyncMock(
            return_value=[mock_user(x, guild_id) for x in range(10)]
        )
        checkmark_reaction.users.return_value = checkmark_users
        # create voice channel
        txt_channel = MagicMock(spec=["send", "set_permissions"])
        voice_channel = MagicMock(spec=["set_permissions"])
        teams_category.create_text_channel = AsyncMock(return_value=txt_channel)
        teams_category.create_voice_channel = AsyncMock(return_value=voice_channel)
        voice_channel.set_permissions = AsyncMock()
        txt_channel.set_permissions = AsyncMock()
        txt_channel.send = AsyncMock()
        asyncio.run(make_atomic_teams(guild_id))
        self.assertEqual(txt_channel.send.call_count, 6)
        self.assertTrue(
            txt_channel.send.call_args_list[4]
            .kwargs["embed"]
            .url.endswith("America%2FNew_York")
        )
