import asyncio

import discord
import numpy as np

import utils
from utils import Numbers


class Board:
    """Class that contains the board of the game, allows to add a token in it,
    and checks if the board has a winning configuration."""


    def __init__(self, size_x, size_y):
        self.size_x = size_x
        self.size_y = size_y
        self.board = np.zeros((size_x, size_y), dtype=int)
        self.winning_move = (slice(0, 0), slice(0, 0))


    def player_play(self, player, column):
        """Add a player token (1 or 2) to the requested column."""

        if self.board[column, 0] == 0:  # if there is room
            for i, r in enumerate(self.board[column]):
                if r != 0:
                    row = i - 1
                    break
            else:
                row = -1

            self.board[column, row] = player

        else:
            raise ValueError('Column is full.')


    def check_winner(self, player):
        """Check if the board has a winning configuration for the player."""

        # THIS IS A MESS
        # vertical
        for c in range(self.size_x):
            for r in range(self.size_y - 3):
                s = (c, slice(r, r + 4))
                if (self.board[s] == player).all():
                    self.winning_move = s
                    return True
        # horizontal
        for c in range(self.size_x - 3):
            for r in range(self.size_y):
                s = (slice(c, c + 4), r)
                if (self.board[s] == player).all():
                    self.winning_move = s
                    return True
        # diagonal down
        for c in range(self.size_x - 3):
            for r in range(self.size_y - 3):
                s = (np.arange(c, c + 4), np.arange(r, r + 4))
                if (self.board[s] == player).all():
                    self.winning_move = s
                    return True
        # diagonal up
        for c in range(3, self.size_x):
            for r in range(self.size_y - 3):
                s = (np.arange(c, c - 4, -1), np.arange(r, r + 4))
                if (self.board[s] == player).all():
                    self.winning_move = s
                    return True

        return False


    def __repr__(self):
        """Represents the board visually, for debug purposes."""

        rep = '\n'.join(str(line) for line in self.board.T)
        return rep


class Connect4:
    """Class that contains the Connect-4 game."""


    def __init__(self, ctx, bot, other_player):
        self.ctx = ctx
        self.bot = bot
        self.players = [ctx.author, other_player]

        size_x, size_y = 7, 6
        self.board = Board(size_x, size_y)
        self.max_turns = size_x * size_y
        self.emoji_numbers = [Numbers[f'_{i}'].value for i in range(1, size_x + 1)]
        self.winner = 0
        self.turn = 0

        self.embed = discord.Embed(title=None, type='rich', color=np.random.randint(0xFFFFFF),  # Random color
        ).add_field(name='Connect 4', value=None,  # will be filled later
        )


    async def play(self):
        """Play a game of Connect 4!"""

        player = 0
        tokens = [utils.Connect4.RED.value, utils.Connect4.BLUE.value]
        hint_message = 'Please wait, setting things up...'
        self.update_embed(hint_message, player)
        self.message_game = await self.ctx.send(embed=self.embed)
        for number in self.emoji_numbers:
            await self.message_game.add_reaction(number)

        while self.winner == 0 and self.turn < self.max_turns:
            hint_message = (f'It is {self.players[player].display_name}\'s turn! '
                            f'{tokens[player]}')
            self.update_embed(hint_message, player)
            await self.message_game.edit(embed=self.embed)


            def check(reaction, user):
                valid = user == self.players[
                    player] and reaction.message.id == self.message_game.id and reaction.emoji in self.emoji_numbers
                return valid


            try:
                reaction, user = await self.bot.wait_for('reaction_add', timeout=5 * 60,  # 5 minutes
                    check=check, )
            except asyncio.TimeoutError as e:
                # makes the other player (not in turn) the winner if
                # the current player times out
                if player == 0:
                    self.winner = 2
                else:  # player == 1
                    self.winner = 1
                player = (player + 1) % 2

                break

            column = self.emoji_numbers.index(reaction.emoji)
            await reaction.remove(user)

            try:
                self.board.player_play(player + 1, column)
            except ValueError:
                hint_message = 'Column is full, you can\'t do that!'
                self.update_embed(hint_message, player)
                await self.message_game.edit(embed=self.embed)
                await asyncio.sleep(2)
                continue  # skips the rest, restart the iteration

            if self.board.check_winner(player + 1):
                self.winner = player + 1

            else:
                player = (player + 1) % 2
                self.turn += 1

        if self.winner != 0:
            hint_message = (f'{self.players[player].display_name} won! '
                            f'{tokens[player]}')
        else:
            hint_message = f'It is a tie!'

        self.update_embed(hint_message, player)
        await self.message_game.edit(embed=self.embed)
        await self.message_game.clear_reactions()


    def update_embed(self, hint_message, player):
        """Edit the Embed with the current board state, and who's
        next to play.
        """
        self.embed.set_author(name=self.players[player].display_name,
            icon_url=self.players[player].avatar_url_as(static_format='png'), ).set_field_at(index=0,  # graphics
            name=self.embed.fields[0].name, value=self.make_graphics(), ).set_footer(text=hint_message, )


    def make_graphics(self):
        """Return a string that represents the board state."""

        tokens = [utils.Connect4.BLACK.value, utils.Connect4.RED.value, utils.Connect4.BLUE.value, ]
        tokens_win = [None, utils.Connect4.RED_WIN.value, utils.Connect4.BLUE_WIN.value, ]

        int_to_emoji = np.vectorize(lambda i: tokens[i])
        graphics = int_to_emoji(self.board.board)

        if self.winner != 0:
            graphics[self.board.winning_move] = tokens_win[self.winner]

        graphics_str = '\n'.join(''.join(i for i in col) for col in graphics.T)
        graphics_str += '\n' + ''.join(self.emoji_numbers)

        return graphics_str