DISCORD_GUILD_CONFIG = {
    699390284416417842: {  # SS
        # alliance
        "alliance_slug": "TestAlliance",
        "coworking_category": 815777518699020318,
        "atomic_team_signup_channel_id": 874091378555117630,
        "atomic_team_signup_msg_id": 874091395143585844,
        "atomic_team_category": 874096677487792158,
        "archived_atomic_team_category": 874096726707957770,
        "default_atomic_team_time": {
            "date": 3,
            "hour": 14,
            "minute": 30,
        },
    },
    742405250731999273: {  # TD
        # alliance
        "alliance_slug": "ThinkDivergent",
        # onboarding
        "onboarding_category": 919013239755522071,
        "onboarding_challenge": "",
        # coworking
        "coworking_category": 897800785423917056,
        # atomic teams
        "atomic_team_signup_channel_id": 792039815327645736,
        "atomic_team_signup_msg_id": 812836894013915176,
        "atomic_team_category": 812829505013809182,
        "archived_atomic_team_category": 812862635333648435,
    },
    968468250495160330: {  # WID
        # onboarding
        "onboarding_category": 968511381378859068,
        "onboarding_challenge": "Find one person from the last cohort with a marketing background.",
        # coworking
        "coworking_category": 968511008840777838,
        # atomic teams
        "atomic_team_signup_channel_id": 968508386280894564,
        "atomic_team_signup_msg_id": 968534978952564736,
        "atomic_team_category": 968536012458430544,
        "archived_atomic_team_category": 968536082494922812,
        "default_atomic_team_time": {
            "date": 3,
            "hour": 14,
            "minute": 30,
        },
    },
}


def get_discord_server_config(guild_id):
    return DISCORD_GUILD_CONFIG.get(guild_id)


SERVER_CONFIG = {
    # born global
    "T01ADE7GFG8": {
        "alliance_slug": "BornGlobal",
        "community_name": "Born Global",
        "community_manager_id": "U02UWR8ALGY",
        "intro_channel_id": "C021BUWHPC0",
        "team_join_config": {
            "reactions": [
                {
                    "type": "dm",
                    "template": "*Welcome to the {community} community {user}!*\n\n"
                    "Feel free to introduce yourself in {intro_channel} with the template below if you'd like.\n\n\n"
                    ":wave: Who are you & What do you love about what you do?\n"
                    ":round_pushpin: Where are you based + timezone?\n"
                    ":partying_face: One fun fact about you!\n"
                    ":raised_hands: What got you excited to join the community?"
                    "\n\n\n"
                    "*About me*\n"
                    "I'm a bot created by {community_manager} the community architect at {community}.\n"
                    "Don't hesitate to reach out if you have any questions or need help with anything here!",
                    "image_attachment": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                },
            ]
        },
        "member_join_channel_config": {
            # general
            "C0198SGS0J3": {
                "reactions": [
                    {
                        "type": "dm",
                        "template": "*Welcome to the {community} community {user}!*\n\n"
                        "Feel free to introduce yourself in {intro_channel} with the template below if you'd like.\n\n\n"
                        ":wave: Who are you & What do you love about what you do?\n"
                        ":round_pushpin: Where are you based + timezone?\n"
                        ":partying_face: One fun fact about you!\n"
                        ":raised_hands: What got you excited to join the community?"
                        "\n\n\n"
                        "*About me*\n"
                        "I'm a bot created by {community_manager} the community architect at {community}.\n"
                        "Don't hesitate to reach out if you have any questions or need help with anything here!",
                        "image_attachment": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                    },
                ]
            },
            # test1
            "C02BQB21ZUM": {
                "reactions": [
                    {
                        "type": "dm",
                        "template": "*Welcome to the {community} community {user}!*\n\n"
                        "Feel free to introduce yourself in {intro_channel} with the template below if you'd like.\n\n\n"
                        ":wave: Who are you & What you are working on?\n"
                        ":round_pushpin: Where are you based + timezone?\n"
                        ":partying_face: One fun fact about you!\n"
                        ":raised_hands: What got you excited to join the community?"
                        "\n\n\n"
                        "*About me*\n"
                        "I'm a bot created by {community_manager} the community architect at {community}.\n"
                        "Don't hesitate to reach out if you have any questions or need help with anything here!",
                        "image_attachment": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                    },
                ]
            },
        },
    },
    # Pookie Dev
    "T10RCBTFZ": {
        "alliance_slug": "ThinkDivergent",
        "community_name": "Pookie Dev",
        "community_manager_id": "U10RD9Q4D",
        "intro_channel_id": "C10RJ0NTT",
        "team_join_config": {
            "reactions": [
                {
                    "type": "dm",
                    "template": "*Welcome to the {community} community {user}!*\n\n"
                    "Feel free to introduce yourself in {intro_channel} with the template below if you'd like.\n\n\n"
                    ":wave: Who are you & What you are working on?\n"
                    ":round_pushpin: Where are you based + timezone?\n"
                    ":partying_face: One fun fact about you!\n"
                    ":raised_hands: What got you excited to join the community?"
                    "\n\n\n"
                    "*About me*\n"
                    "I'm a bot created by {community_manager} the community architect at {community}.\n"
                    "Don't hesitate to reach out if you have any questions or need help with anything here!",
                    "image_attachment": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                },
            ]
        },
        "member_join_channel_config": {
            # public-channel-pookie-test
            "C034BNA1HTP": {
                "reactions": [
                    {
                        "type": "dm",
                        "template": "*Welcome to {community} {user}!*\n\n"
                        "Feel free to introduce yourself in {intro_channel} with the template below if you'd like.\n\n\n"
                        ":wave: Who are you & What you are working on?\n"
                        ":round_pushpin: Where are you based + timezone?\n"
                        ":partying_face: One fun fact about you!\n"
                        ":raised_hands: What got you excited to join the community?"
                        "\n\n\n"
                        "*About me*\n"
                        "I'm a bot created by {community_manager} the community architect at {community}.\n"
                        "Don't hesitate to reach out if you have any questions or need help with anything here!",
                        "image_attachment": "https://media.giphy.com/media/xsE65jaPsUKUo/giphy.gif",
                    },
                ]
            }
        },
    },
}


def get_slack_server_config(payload):
    team = payload.get("team", payload.get("team_id"))
    if not team:
        team = payload.get("user", {}).get("team_id")
    return SERVER_CONFIG.get(team)
