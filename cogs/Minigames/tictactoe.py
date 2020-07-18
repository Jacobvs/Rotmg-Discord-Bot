import asyncio

import discord
import numpy as np

import utils


class Board:
    """Class that contains the board of the game, allows to add a token in it,
    and checks if the board has a winning configuration."""

    def __init__(self):
        self.board = np.zeros(9, dtype=int)

    def player_play(self, player, position):
        """Add a player token (1 or 2) to the requested position."""

        if self.board[position] == 0:
            self.board[position] = player
        else:
            raise ValueError('Position already taken.')

    def check_winner(self, player):
        """Check if the board has a winning configuration for the player."""

        # vertical
        for c in range(3):
            if (self.board[c::3] == player).all():
                return True

        # horizontal
        for r in range(3):
            if (self.board[3 * r:3 * r + 3] == player).all():
                return True

        # diagonal down
        if (self.board[::4] == player).all():
            return True

        # diagonal up
        if (self.board[2:7:2] == player).all():
            return True

        return False

    def __repr__(self):
        """Represents the board visually, for debug purposes."""

        rep = '\n'.join(str(line) for line in self.board.T)
        return rep


class TicTacToe:
    """Class that contains the Tic-Tac-Toe game."""

    def __init__(self, ctx, bot, other_player):
        self.ctx = ctx
        self.bot = bot
        self.players = [ctx.author, other_player]

        self.board = Board()
        self.emoji_positions = [x.value for x in list(utils.TicTacToe)[:9]]
        self.winner = 0

        self.embed = discord.Embed(
            title=None,
            type='rich',
            color=np.random.randint(0xFFFFFF),  # Random color
            ).add_field(
            name='Tic-Tac-Toe',
            value=None,  # will be filled later
            )

    async def play(self):
        """Play a game of Tic-Tac-Toe!"""

        player = 0
        turn = 0
        tokens = [utils.TicTacToe.O.value, utils.TicTacToe.X.value]
        hint_message = 'Please wait, setting things up...'
        self.update_embed(hint_message, player)
        self.message_game = await self.ctx.send(embed=self.embed)
        for pos in self.emoji_positions:
            await self.message_game.add_reaction(pos)

        while self.winner == 0 and turn < 9:
            hint_message = (
                f'It is {self.players[player].display_name}\'s turn! '
                f'{tokens[player]}'
                )
            self.update_embed(hint_message, player)
            await self.message_game.edit(embed=self.embed)

            def check(reaction, user):
                valid = user == self.players[player] \
                    and reaction.message.id == self.message_game.id \
                    and reaction.emoji in self.emoji_positions
                return valid

            try:
                reaction, user = await self.bot.wait_for(
                    'reaction_add',
                    timeout=5 * 60,  # 5 minutes
                    check=check,
                    )
            except asyncio.TimeoutError as e:
                # makes the other player (not in turn) the winner if
                # the current player times out
                if player == 0:
                    self.winner = 2
                else:  # player == 1
                    self.winner = 1
                player = (player + 1) % 2

                break

            position = self.emoji_positions.index(reaction.emoji)

            async for member in reaction.users():
                await reaction.remove(member)

            try:
                self.board.player_play(player + 1, position)
            except ValueError:
                hint_message = 'Try another position.'
                self.update_embed(hint_message, player)
                await self.message_game.edit(embed=self.embed)
                await asyncio.sleep(2)
                continue  # skips the rest, restart the iteration

            if self.board.check_winner(player + 1):
                self.winner = player + 1

            else:
                player = (player + 1) % 2
                turn += 1

        if self.winner != 0:
            hint_message = (
                f'{self.players[player].display_name} won! '
                f'{tokens[player]}'
                )
        else:
            hint_message = f'It is a tie!'

        self.update_embed(hint_message, player)
        await self.message_game.edit(embed=self.embed)
        await self.message_game.clear_reactions()


    def update_embed(self, hint_message, player):
        """Edit the Embed with the current board state, and who's
        next to play.
        """
        self.embed.set_author(
            name=self.players[player].display_name,
            icon_url=self.players[player].avatar_url_as(static_format='png'),
            ).set_field_at(
            index=0,  # graphics
            name=self.embed.fields[0].name,
            value=self.make_graphics(),
            ).set_footer(
            text=hint_message,
            )

    def make_graphics(self):
        """Return a string that represents the board state."""

        tokens = [utils.TicTacToe.BLANK.value, utils.TicTacToe.O.value, utils.TicTacToe.X.value]

        int_to_emoji = np.vectorize(lambda i: tokens[i])
        graphics = int_to_emoji(self.board.board).reshape((3, 3))

        graphics_str = '\n'.join(' '.join(i for i in col)
            for col in graphics)

        return graphics_str