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
