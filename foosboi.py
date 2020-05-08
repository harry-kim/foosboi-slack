from datetime import datetime
import itertools
import math
import random
from contextlib import contextmanager
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, DateTime, and_, or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from typing import List
from trueskill import Rating, rate, BETA, global_env


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

def get(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance

def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        return instance

def get_first_unfinished_game(session):
    return get_or_create(session, Game, team1_score=None)

def get_all_unfinished_games(session):
    return session.query(Game).filter_by(team1_score=None)

def get_nth_unfinished_game(session, n):
    row_number_column = func.row_number().over(order_by=Game.date.desc()).label('row_number')
    query = session.query(Game)
    #query = query.filter(Foo.time_key <= time_key)
    query = query.add_column(row_number_column)
    query = query.from_self().filter(row_number_column == n)
    return query

def get_all_finished_games(session, **kwargs):
    return session.query(Game).filter(and_(Game.team1_score!=None, Game.team2_score != None)).order_by(Game.date)

def get_games_with_player(session, player_id):
    return get_all_finished_games(session).filter(or_(Game.team1_player1==player_id, Game.team1_player2==player_id,
        Game.team2_player1==player_id,
        Game.team2_player2==player_id))

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    user_id = Column(String)
    name = Column(String)
    real_name = Column(String)
    rank = Column(Integer)
    true_skill = Column(Float)
    balance = Column(Float, default=100.0)

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

    def shuffle(self):
        players = [self.team1_player1, self.team1_player2, self.team2_player1, self.team2_player2]
        random.shuffle(players)
        self.team1_player1, self.team1_player2, self.team2_player1, self.team2_player2 = players


class Foosboi():
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
        with session_scope() as session:
            game = Game()
            session.add(game)
            self.games.append(game)
            for user in players_info:
                user = get_or_create(session, 
                        User, 
                        user_id=user["user"]["id"], 
                        real_name=user["user"]["real_name"],
                        name=user["user"]["name"])
                users.append(user)
                game.add_player(user)


            game_num = get_all_unfinished_games(session).count() - 1
            return ("Game {}:\n"
                   "{} and {}\n"
                   "vs.\n"
                   "{} and {}\n".format(game_num,
                                        game.team1_player1,
                                        game.team1_player2,
                                        game.team2_player1,
                                        game.team2_player2))
    def get_games(self) -> str:
        message = ""
        with session_scope() as session:
            games = get_all_unfinished_games(session)
            for i, game in enumerate(games):
                message += (f"Game {i}:\n"
                       "{} and {}\n"
                       "vs.\n"
                       "{} and {}\n".format(game.team1_player1,
                                            game.team1_player2,
                                            game.team2_player1,
                                            game.team2_player2))

            if games.count() == 0:
                message = "No games started."
        return message
 

    def add_players(self, players_info:List[dict]) -> str:
        users = []
        user = players_info[0]

        with session_scope() as session:
            for user in players_info:
                user = get_or_create(session, 
                        User, 
                        user_id=user["user"]["id"], 
                        real_name=user["user"]["real_name"],
                        name=user["user"]["name"])
                users.append(user)

            games = get_all_unfinished_games(session)
            message = ""
            for game in games:
                if game.spaces_left() >= len(users):
                    for user in users:
                        game.add_player(user)
                        message += "{} joined the next game!\n".format(user.real_name)
                    break

            if game.spaces_left() == 0:
                winp = round(self.balance(game) * 100, 1)
                message += """
                *Next game is ready to go!*
                <@{}> and <@{}> ({}%)
                vs.
                <@{}> and <@{}> ({}%)
                """.format(game.team1_player1.user_id,
                           game.team1_player2.user_id,
                           winp,
                           game.team2_player1.user_id,
                           game.team2_player2.user_id,
                           100-winp)

            return message

    def balance(self, game):
        stats = self.stats()
        orders = [[0,1,2,3], [0,2,1,3], [0,3,1,2]]
        percentages = [0, 0, 0]
        players = [game.team1_player1, game.team1_player2, game.team2_player1, game.team2_player2]

        for i, order in enumerate(orders):
            p1 = self.retrieve_player_stats(stats, players[order[0]].name)
            p2 = self.retrieve_player_stats(stats, players[order[1]].name)
            p3 = self.retrieve_player_stats(stats, players[order[2]].name)
            p4 = self.retrieve_player_stats(stats, players[order[3]].name)
            percentages[i] = self.win_probability([p1,p2], [p3,p4])

        closest = 0
        if abs(percentages[1] - 0.5) < abs(percentages[0] - 0.5):
            closest = 1
        if abs(percentages[2] - 0.5) < abs(percentages[closest] - 0.5):
            closest = 2
        print(closest)
        
        with session_scope() as session:
            game.team1_player1 = players[orders[closest][0]]
            game.team1_player2 = players[orders[closest][1]]
            game.team2_player1 = players[orders[closest][2]]
            game.team2_player2 = players[orders[closest][3]]

        return percentages[closest]


    def shuffle(self, game_num=0):
        with session_scope() as session:
            game = get_all_unfinished_games(session)[game_num]
            game.shuffle()
            rankings = self.stats()
            team1 = [rankings[game.team1_player1.name], rankings[game.team1_player2.name]]
            team2 = [rankings[game.team2_player1.name], rankings[game.team2_player2.name]]
            winp = round(self.win_probability(team1, team2) * 100, 1)
            message = """
                *Shuffled Teams!*
                <@{}> and <@{}> ({}%)
                vs.
                <@{}> and <@{}> ({}%)
                """.format(game.team1_player1.user_id,
                           game.team1_player2.user_id,
                           winp,
                           game.team2_player1.user_id,
                           game.team2_player2.user_id,
                           100-winp)

        return message


    
    def win_probability(self, team1, team2):
        delta_mu = sum(r['mu'] for r in team1) - sum(r['mu'] for r in team2)
        sum_sigma = sum(r['sigma'] ** 2 for r in itertools.chain(team1, team2))
        size = len(team1) + len(team2)
        denom = math.sqrt(size * (BETA * BETA) + sum_sigma)
        ts = global_env()
        return ts.cdf(delta_mu / denom)


    def cancel_game(self, game_num:int):
        with session_scope() as session:
            game = get_all_unfinished_games(session)[game_num]
            session.delete(game)

        return f"Game {game_num} cancelled!"

    def cancel_all_games(self):
        with session_scope() as session:
            get_all_unfinished_games(session).delete()

        return f"All games cancelled!"


    def finish_game(self, team1_score:int, team2_score:int):
        with session_scope() as session:
            game = get_first_unfinished_game(session)
            game.team1_score = team1_score
            game.team2_score = team2_score

            session.commit()

            message = "Results saved\n" 
            if team1_score > team2_score:
                message += f"Winners: <@{game.team1_player1.user_id}> and <@{game.team1_player2.user_id}>\n" 
                message += f"Losers: <@{game.team2_player1.user_id}> and <@{game.team2_player2.user_id}>\n"
            else:
                message += f"Winners: <@{game.team2_player1.user_id}> and <@{game.team2_player2.user_id}>\n" 
                message += f"Losers: <@{game.team1_player1.user_id}> and <@{game.team1_player2.user_id}>\n"

        return message

    def retrieve_player_stats(self, stats, player):
        if player in stats:
            return stats[player]

        return {
                "gamesPlayed": 0,
                "gamesWon": 0,
                "winPercentage": 0,
                "skill": Rating(),
                "mu": 0,
                "sigma": 0,
                "rank": 2,
                "streak": 0,
                "longestWinStreak": 0,
                "longestLoseStreak": 0,
        }

    def stats(self):
        stats = {}

        with session_scope() as session:
            finished_games = get_all_finished_games(session)

            for game in finished_games:
                t1p1 = game.team1_player1.name
                t1p2 = game.team1_player2.name
                t2p1 = game.team2_player2.name
                t2p2 = game.team2_player2.name

                t1score = game.team1_score
                t2score = game.team2_score

                all_players = [t1p1, t1p2, t2p1, t2p2]

                for player in all_players:
                    stats[player] = self.retrieve_player_stats(stats, player)
                    stats[player]['gamesPlayed'] += 1
                    stats[player]['rank'] = 2

                winners = [t1p1, t1p2] if t1score > t2score else [t2p1, t2p2]
                losers = [t1p1, t1p2] if t1score < t2score else [t2p1, t2p2]

                for winner in winners:
                    stats[winner]['gamesWon'] += 1
                    stats[winner]['rank'] = 1

                    stats[winner]['streak'] = 1 if stats[winner]['streak'] < 0 else stats[winner]['streak'] + 1
                    if stats[winner]['streak'] > stats[winner]['longestWinStreak']:
                        stats[winner]['longestWinStreak'] = stats[winner]['streak']

                for loser in losers:
                    stats[loser]['streak'] = -1 if stats[loser]['streak'] > 0 else stats[loser]['streak'] - 1
                    if -stats[loser]['streak'] > stats[loser]['longestLoseStreak']:
                        stats[loser]['longestLoseStreak'] = -stats[loser]['streak']


                # TODO: trueskill adjust
                w1 = stats[winners[0]]['skill']
                w2 = stats[winners[1]]['skill']
                l1 = stats[losers[0]]['skill']
                l2 = stats[losers[1]]['skill']
                (w1, w2),(l1,l2) = rate([[w1,w2], [l1,l2]])
                stats[winners[0]]['skill'] = w1
                stats[winners[1]]['skill'] = w2
                stats[losers[0]]['skill'] = l1
                stats[losers[1]]['skill'] = l2
            for player in stats.keys():
                stats[player]['name'] = player
                stats[player]['winPercentage'] = round(stats[player]['gamesWon'] / stats[player]['gamesPlayed'] * 100, 2)
                stats[player]['trueskill'] = round(stats[player]['skill'].mu - (3 * stats[player]['skill'].sigma), 2)
                # From Wikipedia
                # Player ranks are displayed as the conservative estimate of their skill, R = μ − 3 × σ. This is conservative, because the system is 99% sure that the player's skill is actually higher than what is displayed as their rank.


                stats[player]['mu'] = round(stats[player]['skill'].mu, 2)
                stats[player]['sigma'] = round(stats[player]['skill'].sigma, 2)

            return stats

    def get_rankings(self):
        stats = self.stats()

        # remove retirees

        rankings = sorted(stats.items(), key=lambda player_stat: player_stat[1]['trueskill'], reverse=True)

        for i, player in enumerate(rankings):
            player[1]['rank'] = str(i+1)

        return rankings

    def noopFormat(self, s): return s
    def trueSkillFormat(self, s): return s
    def percentFormat(self, s): return "{}%    ".format(s)
    def gamesFormat(self, s): return "{} game{}".format(s, '' if s==1 else 's')
    def streakFormat(self, s):
        winning = int(s) > 0
        return "{}{} {}".format("🔥" if winning else "💩", abs(int(s)), "won" if winning else "lost")

    def add_column(self, lines, stats, header, field, format_func=None, first_column=None):
        format_func = format_func or self.noopFormat
        longest_length = longest_header_length = len(header)

        for i, stat in enumerate(stats):
            field_value = format_func(stat[1][field]) if field != 'rank' else i
            longest_length = max(longest_length, len(str(field_value)))
            longest_header_length = max(longest_header_length, len(str(field_value)))

        longest_length += 1
        longest_header_length += 1

        # Add header and underline
        header_length = longest_header_length + 2
        lines[0] += header.ljust(header_length)
        lines[1] += '=' * header_length

        # Add the column per stat
        for i, stat in enumerate(stats):
            field_value = format_func(str(stat[1][field])).ljust(longest_header_length)
            print(field_value)

            if not first_column:
                lines[2+i] += "| "

            lines[2+i] += field_value

    def print_stats(self):
        with session_scope() as session:
            rankings = self.get_rankings()

            response_list = [''] * (len(rankings)+2)
            self.add_column(response_list, rankings, "Rank", "rank", self.noopFormat, True)
            self.add_column(response_list, rankings, "Player", "name")
            self.add_column(response_list, rankings, "Trueskill", "trueskill", self.trueSkillFormat)
            self.add_column(response_list, rankings, "Mu", "mu", self.trueSkillFormat)
            self.add_column(response_list, rankings, "sigma", "sigma", self.trueSkillFormat)
            self.add_column(response_list, rankings, "Win %", "winPercentage", self.percentFormat)
            self.add_column(response_list, rankings, "Won", "gamesWon")
            self.add_column(response_list, rankings, "Played", "gamesPlayed")
            self.add_column(response_list, rankings, "Streak", "streak", self.streakFormat)
            self.add_column(response_list, rankings, "Longest Win Streak", "longestWinStreak", self.gamesFormat)
            self.add_column(response_list, rankings, "Longest Loss Streak", "longestLoseStreak", self.gamesFormat)

        output = ""
        chunks = [response_list[x:x+30] for x in range(0, len(response_list), 30)]
        for chunk in chunks:
            output =  ""
            output += "```"
            for line in chunk:
                output += line
                output += "\n"
            output += "```"
            output += "\n\n"
            return output

    def history(self, player_name:str, num_games:int):
        with session_scope() as session:
            player = get_or_create(session, User, name=player_name)
            games = get_games_with_player(session, player_id=player)[:num_games]
            msg = ""
            for game in games:
                msg += f"{game.team1_score}-{game.team2_score}\t{game.team1_player1.name} and {game.team1_player2.name}" \
                        f"\tvs.\t{game.team2_player1.name} and {game.team2_player2.name}\n"
            return msg

    def get_balance(self, user:str) -> str:
        with session_scope() as session:
            player = get(session, 
                    User, 
                    user_id=user["user"]["id"])
            balance = str(player.balance)
            msg = f"{player} has {balance} fooscoin left"
            return msg
        
    def rebuy(self, user:str) -> str:
        with session_scope() as session:
            player = get(session, 
                    User, 
                    user_id=user["user"]["id"])
            if player.balance <= 0:
                player.balance = 100
                msg = "The foosgods have taken pity on you. You are given 100 fooscoin!"
            else:
                msg = "You are too rich... keep losing!"
            return msg
 


engine = create_engine('sqlite:///foosboi.db', echo=True)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
