from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import List

Base = declarative_base()


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    name = Column(String)
    real_name = Column(String)
    rank = Column(Integer)
    true_skill = Column(Float)
    balance = Column(Float)

    def __repr__(self):
        return f"User {self.id} {self.name} {self.rank} {self.true_skill}"

    def __str__(self):
        return self.real_name


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime)
    team1_player1 = Column(Integer, ForeignKey('users.id'))
    team1_player2 = Column(Integer, ForeignKey('users.id'))
    team2_player1 = Column(Integer, ForeignKey('users.id'))
    team2_player2 = Column(Integer, ForeignKey('users.id'))
    team1_score = Column(Integer)
    team2_score = Column(Integer)

    def spaces_left(self):
        spaces = 0
        if not team1_player1:
            spaces += 1
        if not team1_player2:
            spaces += 1
        if not team2_player1:
            spaces += 1
        if not team2_player1:
            spaces += 1
        return spaces



class Foosboi():
    NEW_GAME_BLOCK = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "Game 1"
        }
    }

    def get_player_block(self):
        task_checkmark = self._get_checkmark(self.pin_task_completed)
        text = (
            f"{task_checkmark} *Pin this message* :round_pushpin:\n"
        )
        information = (
            ":information_source: *<https://get.slack.help/hc/en-us/articles/205239997-Pinning-messages-and-files"
            "|Learn How to Pin a Message>*"
        )
        return self._get_task_block(text, information)

    @staticmethod
    def _get_checkmark(task_completed:bool) -> str:
        if task_completed:
            return ":white_check_mark:"
        return ":white_large_square:"

    @staticmethod
    def _get_task_block(text, information):
        return [
            {"type": "section", "text": {"type": "mrkdwn", "text": text}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": information}]},
        ]

    PLAYER_BLOCK = {
			"type": "section",
			"fields": [
				{
					"type": "mrkdwn",
					"text": "*Player 1:*\n{}"
				},
				{
					"type": "mrkdwn",
					"text": "*Player 2:*\nJoe"
				},
				{
					"type": "mrkdwn",
					"text": "*Player 3:*\na"
				},
				{
					"type": "mrkdwn",
					"text": "*Player 4:*\ng"
				}
			]
		}

    ACTIONS_BLOCK = {
			"type": "actions",
			"elements": [
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Join Game"
					},
					"style": "primary",
					"value": "click_me_123"
				},
				{
					"type": "button",
					"text": {
						"type": "plain_text",
						"emoji": True,
						"text": "Leave Game"
					},
					"style": "danger",
					"value": "click_me_123"
				}
			]
		}

    def __init__(self, channel=None):
        engine = create_engine('sqlite:///foosboi.db', echo=True)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        self.session = Session()
        self.channel = channel
        self.username = "foosbot-py"
        self.icon_emoji = ":robot_face:"
        self.timestamp = ""
        self.pin_task_completed = False
        self.games = []

    @property
    def channel():
        return self.__channel
    
    @channel.setter
    def channel(self, channel):
        self.__channel = channel

    def get_message_payload(self):
        return {
            "ts": self.timestamp,
            "channel": self.channel,
            "username": self.username,
            "icon_emoji": self.icon_emoji,
            "blocks": [self.NEW_GAME_BLOCK,
                       self.PLAYER_BLOCK,
                       self.ACTIONS_BLOCK,
                       *self.get_player_block()]
        }


    def start_game(self, players_info:List[dict]) -> str:
        users = []
        for user in players_info:
            user = get_or_create(self.session, 
                    User, 
                    user_id=user["user"]["id"], 
                    real_name=user["user"]["real_name"],
                    name=user["user"]["name"])
            users.append(user)

        game = Game(team1_player1=users[0])
        self.games.append(game)
        return ("Game 0:\n"
               "{} and {}\n"
               "vs.\n"
               "{} and {}\n".format(game.team1_player1,
                                    game.team1_player2,
                                    game.team2_player1,
                                    game.team2_player2))

    def add_players(self, players:List[str]) -> str:
        for user in players:
            get_or_create(self.session, User, user_id=user["user"]["id"])

        if self.games:
            pass
        return "" 
