import os
import logging
import slack
import ssl as ssl_lib
import certifi
from foosboi import *
from slack import RTMClient
from slack.errors import SlackApiError
from slackeventsapi import SlackEventAdapter
from local_settings import *
from sqlalchemy.orm import sessionmaker
from typing import List

slack_signing_secret = SLACK_SIGNING_SECRET
slack_events_adapter = SlackEventAdapter(slack_signing_secret, "/slack/events")

slack_bot_token = SLACK_BOT_TOKEN

def command(f):
    def wrapped_function(*args, **kwargs):
        try:
            message = f(*args, **kwargs)  # func
            web_client = args[0]
            channel = args[1]
            web_client.chat_postMessage(channel=channel, text=message)
        except SlackApiError as e:
            # You will get a SlackApiError if "ok" is False
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            print(f"Got an error: {e.response['error']}")
    return wrapped_function

@command
def start_game(web_client: slack.WebClient, channel: str, user_id: str):
    user = web_client.users_info(user=user_id)
    message = foosboi.start_game(players_info=[user])

    return message

@command
def add_players(web_client: slack.WebClient, channel: str, players: List[dict]):
    users = []
    for user_id in players:
        user_id = user_id.strip('<@>')
        users.append(web_client.users_info(user=user_id))

    return foosboi.add_players(players_info=users)

@command
def games(web_client: slack.WebClient, channel: str, players: List[dict]):
    return foosboi.get_games()

@command
def cancel_all_games(web_client: slack.WebClient, channel: str):
    return foosboi.cancel_all_games()

@command
def cancel_game(web_client: slack.WebClient, channel: str, game_num: int):
    return foosboi.cancel_game(game_num)

@command
def stats(web_client: slack.WebClient, channel: str):
    return foosboi.print_stats()

@command
def finish_game(web_client: slack.WebClient, channel: str, score:str):
    team1_score, team2_score = map(int, score.split('-'))
    return foosboi.finish_game(team1_score, team2_score)

@command
def shuffle(web_client: slack.WebClient, channel: str, game_num:int):
    return foosboi.shuffle(game_num)

@command
def history(web_client: slack.WebClient, channel: str, user:str, num_games:int):
    return foosboi.history(user, num_games)

@command
def balance(web_client: slack.WebClient, channel: str, user_id:str):
    user_id = user_id.strip('<@>')
    user = web_client.users_info(user=user_id)
    return foosboi.get_balance(user)

@command
def rebuy(web_client: slack.WebClient, channel: str, user_id:str):
    user = client.users_info(user=user_id)
    return foosboi.rebuy(user)

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


# ============== Message Events ============= #
# When a user sends a DM, the event type will be 'message'.
# Here we'll link the message callback to the 'message' event.
@slack.RTMClient.run_on(event="message")
def message(**payload):
    """
    Handle commands
    """
    data = payload["data"]
    client = payload["web_client"]
    channel_id = data.get("channel")
    user_id = data.get("user")
    thread_ts = data.get("thread_ts")
    text = data.get("text")

    try:
        if "start" in text:
            response = start_game(client, channel_id, user_id)
        elif "games" in text:
            response = games(client, channel_id, user_id)
        elif "join" in text:
            response = add_players(client, channel_id, [user_id])
        elif "add player" in text:
            players = text.split()[2:]
            response = add_players(client, channel_id, players)
        elif "cancel all" in text:
            response = cancel_all_games(client, channel_id)
        elif "cancel game" in text:
            message_list = text.split()
            game_num = int(message_list[2]) if len(message_list) > 2 else 0
            response = cancel_game(client, channel_id, game_num)
        elif "finish game" in text:
            score = text.split()[2:][0]
            response = finish_game(client, channel_id, score)
        elif "stats" in text:
            response = stats(client, channel_id)
        elif "shuffle" in text:
            message_list = text.split()
            game_num = int(message_list[2]) if len(message_list) > 2 else 0
            response = shuffle(client, channel_id, game_num)
        elif "history" in text:
            message_list = text.split()
            user = message_list[1]
            game_num = message_list[2] if len(message_list) > 2 else 5
            game_num = -1 if game_num == "all" else int(game_num)
            response = history(client, channel_id, user, game_num)
        elif "balance" in text:
            message_list = text.split()
            try:
                user = message_list[1]
            except IndexError:
                user = user_id
            response = balance(client, channel_id, user)
        elif "rebuy" in text:
            message_list = text.split()
            user = user_id
            response = rebuy(client, channel_id, user)
    except Exception as e:
        print(e)
        

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
            add_players(client, channel, players)
        elif "cancel all" in message.get("text"):
            cancel_all_games(client, channel)
        elif "cancel game" in message.get("text"):
            message_list = message.get("text").split()
            game_num = int(message_list[2]) if len(message_list) > 2 else 0
            cancel_game(client, channel, game_num)
        elif "finish game" in message.get("text"):
            score = message.get("text").split()[2:][0]
            finish_game(client, channel, score)
        elif "stats" in message.get("text"):
            stats(client, channel)
        elif "shuffle" in message.get("text"):
            message_list = message.get("text").split()
            game_num = int(message_list[2]) if len(message_list) > 2 else 0
            shuffle(client, channel, game_num)
        elif "history" in message.get("text"):
            message_list = message.get("text").split()
            user = message_list[1]
            game_num = message_list[2] if len(message_list) > 2 else 5
            game_num = -1 if game_num == "all" else int(game_num)
            history(client, channel, user, game_num)
        elif "balance" in message.get("text"):
            message_list = message.get("text").split()
            try:
                user = message_list[1]
            except IndexError:
                user = message['user']
            balance(client, channel, user)
        elif "rebuy" in message.get("text"):
            message_list = message.get("text").split()
            user = message['user']
            rebuy(client, channel, user)




logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
ssl_context = ssl_lib.create_default_context(cafile=certifi.where())
slack_token = SLACK_BOT_TOKEN
foosboi = Foosboi()
rtm_client = slack.RTMClient(token=slack_token, ssl=ssl_context)
rtm_client.start()
#client = slack.WebClient(token=slack_token)

#response = client.chat_postMessage(
#    channel='#bottesters',
#    text="Hello world!")
#assert response["ok"]
#assert response["message"]["text"] == "Hello world!"
#slack_events_adapter.start(port=3000, debug=True)

