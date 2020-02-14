import os
import logging
import slack
import ssl as ssl_lib
import certifi
from tutorial import OnboardingTutorial
from foosboi import *
from slackeventsapi import SlackEventAdapter
from local_settings import *
from sqlalchemy.orm import sessionmaker
from typing import List

slack_signing_secret = SLACK_SIGNING_SECRET
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events")

slack_bot_token = SLACK_BOT_TOKEN

# For simplicity we'll store our app data in-memory with the following data structure.
# onboarding_tutorials_sent = {"channel": {"user_id": OnboardingTutorial}}
onboarding_tutorials_sent = {}

def command(f):
    def wrapped_function(*args, **kwargs):
        message = f(*args, **kwargs)  # func
        web_client = args[0]
        channel = args[1]
        web_client.chat_postMessage(channel=channel, text=message)
    return wrapped_function

@command
def start_game(web_client: slack.WebClient, channel: str, user_id: str):
    # Create a new onboarding tutorial.
    #onboarding_tutorial = OnboardingTutorial(channel)

    # Get the onboarding message payload
    #message = onboarding_tutorial.get_message_payload()
    user = client.users_info(user=user_id)
    message = foosboi.start_game(players_info=[user])
    #message = foosboi.get_message_payload()

    # Post the onboarding message in Slack
    #response = web_client.chat_postMessage(**message)

    # Capture the timestamp of the message we've just posted so
    # we can use it to update the message after a user
    # has completed an onboarding task.
    #onboarding_tutorial.timestamp = response["ts"]
    foosboi.timestamp = response["ts"]

    # Store the message sent in onboarding_tutorials_sent
    if channel not in onboarding_tutorials_sent:
        onboarding_tutorials_sent[channel] = {}
    onboarding_tutorials_sent[channel][user_id] = foosboi

    return message

@command
def add_players(web_client: slack.WebClient, channel: str, players: List[dict]):
    users = []
    for user_id in players:
        user_id = user_id.strip('<@>')
        users.append(client.users_info(user=user_id))

    return foosboi.add_players(players_info=users)

@command
def games(web_client: slack.WebClient, channel: str, players: List[dict]):
    return foosboi.get_games()

@command
def cancel_game(web_client: slack.WebClient, channel: str, game_num: int):
    return foosboi.cancel_game(game_num)

@command
def stats(web_client: slack.WebClient, channel: str):
    return foosboi.stats()

@command
def finish_game(web_client: slack.WebClient, channel: str, score:str):
    team1_score, team2_score = map(int, score.split('-'))
    return foosboi.finish_game(team1_score, team2_score)

# ================ Team Join Event =============== #
# When the user first joins a team, the type of the event will be 'team_join'.
# Here we'll link the onboarding_message callback to the 'team_join' event.
@slack.RTMClient.run_on(event="team_join")
def onboarding_message(**payload):
    """Create and send an onboarding welcome message to new users. Save the
    time stamp of this message so we can update this message in the future.
    """
    # Get WebClient so you can communicate back to Slack.
    web_client = payload["web_client"]

    # Get the id of the Slack user associated with the incoming event
    user_id = payload["data"]["user"]["id"]

    # Open a DM with the new user.
    response = web_client.im_open(user_id)
    channel = response["channel"]["id"]

    # Post the onboarding message.
    start_onboarding(web_client, user_id, channel)


# ============= Reaction Added Events ============= #
# When a users adds an emoji reaction to the onboarding message,
# the type of the event will be 'reaction_added'.
# Here we'll link the update_emoji callback to the 'reaction_added' event.
@slack.RTMClient.run_on(event="reaction_added")
def update_emoji(**payload):
    """Update the onboarding welcome message after receiving a "reaction_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data["item"]["channel"]
    user_id = data["user"]

    if channel_id not in onboarding_tutorials_sent:
        return

    # Get the original tutorial sent.
    onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]

    # Mark the reaction task as completed.
    onboarding_tutorial.reaction_task_completed = True

    # Get the new message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the updated message in Slack
    updated_message = web_client.chat_update(**message)

    # Update the timestamp saved on the onboarding tutorial object
    onboarding_tutorial.timestamp = updated_message["ts"]


# =============== Pin Added Events ================ #
# When a users pins a message the type of the event will be 'pin_added'.
# Here we'll link the update_pin callback to the 'reaction_added' event.
@slack.RTMClient.run_on(event="pin_added")
def update_pin(**payload):
    """Update the onboarding welcome message after receiving a "pin_added"
    event from Slack. Update timestamp for welcome message as well.
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data["channel_id"]
    user_id = data["user"]

    # Get the original tutorial sent.
    onboarding_tutorial = onboarding_tutorials_sent[channel_id][user_id]

    # Mark the pin task as completed.
    onboarding_tutorial.pin_task_completed = True

    # Get the new message payload
    message = onboarding_tutorial.get_message_payload()

    # Post the updated message in Slack
    updated_message = web_client.chat_update(**message)

    # Update the timestamp saved on the onboarding tutorial object
    onboarding_tutorial.timestamp = updated_message["ts"]


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack.RTMClient.run_on(event="message")
def message(**payload):
    """Display the onboarding welcome message after receiving a message
    that contains "start".
    """
    data = payload["data"]
    web_client = payload["web_client"]
    channel_id = data.get("channel")
    user_id = data.get("user")
    text = data.get("text")

    if text and text.lower() == "start":
        return start_onboarding(web_client, user_id, channel_id)


@slack_events_adapter.on("button")
def button_pressed(event_data):
    print("BUTTON PRESSED")


@slack_events_adapter.on("message")
def handle_message(event_data):
    message = event_data["event"]
    if message.get("subtype") is None:
        channel = message["channel"]
        if "start" in message.get("text"):
            start_game(client, channel, message["user"])
        elif "games" in message.get("text"):
            games(client, channel, message["user"])
        elif "join" in message.get("text"):
            add_players(client, channel, [message["user"]])
        elif "add player" in message.get("text"):
            players = message.get("text").split()[2:]
            #users_info = get_users_info(players)
            add_players(client, channel, players)
        elif "cancel game" in message.get("text"):
            message_list = message.get("text").split()
            game_num = int(message_list[2]) if len(message_list) > 2 else 0
            cancel_game(client, channel, game_num)
        elif "finish game" in message.get("text"):
            score = message.get("text").split()[2:][0]
            finish_game(client, channel, score)

        elif "stats" in message.get("text"):
            stats(client, channel)



logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
slack_token = SLACK_BOT_TOKEN
#rtm_client = slack.RTMClient(token=slack_token, ssl=ssl_context)
#rtm_client.start()
foosboi = Foosboi()
client = slack.WebClient(token=slack_token)

response = client.chat_postMessage(
    channel='#bottesters',
    text="Hello world!")
assert response["ok"]
assert response["message"]["text"] == "Hello world!"
slack_events_adapter.start(port=3000, debug=True)

