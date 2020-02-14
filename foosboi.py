from datetime import datetime
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from typing import List


Base = declarative_base()
@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    print (kwargs)
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
#        session.commit()
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
        return f'User {self.id} {self.name} {self.rank} {self.true_skill}'

    def __str__(self):
        return self.real_name


class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, server_default=func.now())
    t1p1_id = Column(Integer, ForeignKey('users.id'))
    t1p2_id = Column(Integer, ForeignKey('users.id'))
    t2p1_id = Column(Integer, ForeignKey('users.id'))
    t2p2_id = Column(Integer, ForeignKey('users.id'))
    team1_score = Column(Integer)
    team2_score = Column(Integer)

    team1_player1 = relationship("User", foreign_keys=[t1p1_id])
    team1_player2 = relationship("User", foreign_keys=[t1p2_id])
    team2_player1 = relationship("User", foreign_keys=[t2p1_id])
    team2_player2 = relationship("User", foreign_keys=[t2p2_id])

    def spaces_left(self):
        spaces = 0
        if not self.team1_player1:
            spaces += 1
        if not self.team1_player2:
            spaces += 1
        if not self.team2_player1:
            spaces += 1
        if not self.team2_player2:
            spaces += 1
        return spaces

    def add_player(self, player:User):
        if not self.team1_player1:
            self.team1_player1 = player
        elif not self.team1_player2:
            self.team1_player2 = player
        elif not self.team2_player1:
            self.team2_player1 = player
        elif not self.team2_player2:
            self.team2_player2 = player


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
        #game = Game()
        with session_scope() as session:
            game = Game()
            session.add(game)
            #session.add(game)
            self.games.append(game)
            for user in players_info:
                user = get_or_create(session, 
                        User, 
                        user_id=user["user"]["id"], 
                        real_name=user["user"]["real_name"],
                        name=user["user"]["name"])
                users.append(user)
                game.add_player(user)


            return ("Game 0:\n"
                   "{} and {}\n"
                   "vs.\n"
                   "{} and {}\n".format(game.team1_player1,
                                        game.team1_player2,
                                        game.team2_player1,
                                        game.team2_player2))
    def get_games(self) -> str:
        message = ""
        for i, game in enumerate(self.games):
            message += (f"Game {i}:\n"
                   "{} and {}\n"
                   "vs.\n"
                   "{} and {}\n".format(game.team1_player1,
                                        game.team1_player2,
                                        game.team2_player1,
                                        game.team2_player2))

        if len(self.games) == 0:
            message = "No games started."
        return message
 

    def add_players(self, players_info:List[dict]) -> str:
        users = []
        user = players_info[0]

#        print(user["user"]["id"])
#        print(user["user"]["real_name"])
#        print(user["user"]["name"])
#        with session_scope() as session:
#            for u in session.query(User).order_by(User.name): #filter_by(user_id=user["user"]["id"]):
#                print(u)
#            return ""
        with session_scope() as session:
        #    p = session.query(User).filter_by(user_id=user["user"]["id"], 
        #                real_name=user["user"]["real_name"],
        #                name=user["user"]["name"]).first()
        #    users.append(p)
            for user in players_info:
                user = get_or_create(session, 
                        User, 
                        user_id=user["user"]["id"], 
                        real_name=user["user"]["real_name"],
                        name=user["user"]["name"])
                users.append(user)

            import pdb; pdb.set_trace()
            game = get_or_create(session, Game, id=self.games[0].id)
            message = ""
            if game.spaces_left() >= len(users):
                for user in users:
                    game.add_player(user)
                    message += "{} joined the next game!\n".format(user.name)
                    
            if game.spaces_left() == 0:
                message += """
                *Next game is ready to go!*
                <@{}> and <@{}> ()
                vs.
                <@{}> and <@{}> ()
                """.format(game.team1_player1.user_id,
                           game.team1_player2.user_id,
                           game.team2_player1.user_id,
                           game.team2_player2.user_id)

            return message

    def cancel_game(self, game_num:int):
        self.games.pop(game_num)
        return f"Game {game_num} cancelled!"

    def finish_game(self, team1_score:int, team2_score:int):
        game = self.games[0]
        #game_instance = get_or_create(self.session, Game, id=game.id)
        #import pdb; pdb.set_trace()

#        game_instance.team1_player1=game.team1_player1
#        game_instance.team1_player2=game.team1_player2
#        game_instance.team2_player1=game.team2_player1
#        game_instance.team2_player2=game.team2_player2
        game.team1_score = team1_score
        game.team2_score = team2_score

        self.session.commit()

        message = "Results saved\n" 
        if team1_score > team2_score:
            message += f"Winners: <@{game.team1_player1.user_id}> and <@{game.team1_player2.user_id}>\n" 
            message += f"Losers: <@{game.team2_player1.user_id}> and <@{game.team2_player2.user_id}>\n"
        else:
            message += f"Winners: <@{game.team2_player1.user_id}> and <@{game.team2_player2.user_id}>\n" 
            message += f"Losers: <@{game.team1_player1.user_id}> and <@{game.team1_player2.user_id}>\n"

        #   "Rank changes:\n" +
        #    "...todo...\n")

        return message

    def stats(self):
        stats = {}
        stat_msg = ""
        for game in self.session.query(Game).order_by(Game.date):
            stat_msg += "{}\n".format(game.__dict__)

        print(stat_msg)
        return stat_msg


engine = create_engine('sqlite:///foosboi.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
