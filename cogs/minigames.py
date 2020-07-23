import numpy as np
from discord.ext import commands

import utils
from cogs.Minigames.connect4 import Connect4
from cogs.Minigames.hangman import Hangman
from cogs.Minigames.highlow import HighLow
from cogs.Minigames.tictactoe import TicTacToe


class Minigames(commands.Cog):
    """Play various minigames against the bot or another member!"""

    def __init__(self, client):
        self.client = client


    @commands.command(usage="connect4 <member>",
                      description="A game of Connect-4 with another member.\nEach player takes turn in placing a token on the board,\n"
                                  "the winner is the first to put four tokens in a row.")
    async def connect4(self, ctx, other_player: utils.MemberLookupConverter):
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument('Cannot play a game against that member.')

        game = Connect4(ctx, self.client, other_player)
        await game.play()


    @commands.command(usage="hangman", description="A game of Hangman with a random word.\nYou guess letters by typing them in chat.")
    async def hangman(self, ctx):
        game = Hangman(ctx, self.client)
        await game.play()


    @commands.command(usage="highlow", aliases=['highlow', 'hilo'],
                      description="A game of Higher-or-Lower.\nThe player plays against the dealer (bot) for half a deck of cards.")
    async def higher_lower(self, ctx):
        game = HighLow(ctx, self.client)
        await game.play()


    @commands.command(usage="tictactoe <member>", description="A game of Tic-Tac-Toe with another member.")
    async def tictactoe(self, ctx, other_player: utils.MemberLookupConverter):
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument('Cannot play a game against that member.')

        game = TicTacToe(ctx, self.client, other_player)
        await game.play()


    @commands.command(usage="rps <choice>", aliases=['rockpaperscissors', 'rps'], description="Play a game of Rock Paper Scissors.")
    async def rock_paper_scissors(self, ctx, player_choice=''):
        options_text= ['rock', 'paper', 'scissors']
        options_emoji = [':full_moon:', ':newspaper:', ':scissors:']

        # Convert answer to lowercase
        player_choice = player_choice.lower()

        # Give the bot a random choice
        i = np.random.randint(3)
        bot_choice = options_text[i]
        bot_choice_message = 'I choose ' + bot_choice + '! ' + options_emoji[i]

        if player_choice in options_text:
            await ctx.send(bot_choice_message)

        player_win_message = 'You won! :cry:'
        bot_win_message = 'You lose! :stuck_out_tongue_closed_eyes:'

        # Now to work out who won"
        if player_choice == bot_choice:
            await ctx.send('It\'s a draw!')
        elif (player_choice == 'rock') and (bot_choice == 'scissors'):
            await ctx.send(player_win_message)
        elif (player_choice == 'rock') and (bot_choice == 'paper'):
            await ctx.send(bot_win_message)
        elif (player_choice == 'paper') and (bot_choice == 'rock'):
            await ctx.send(player_win_message)
        elif (player_choice == 'paper') and (bot_choice == 'scissors'):
            await ctx.send(bot_win_message)
        elif (player_choice == 'scissors') and (bot_choice == 'paper'):
            await ctx.send(player_win_message)
        elif (player_choice == 'scissors') and (bot_choice == 'rock'):
            await ctx.send(bot_win_message)
        # Easter eggs!
        elif player_choice == 'spock':
            await ctx.send('Live long and prosper :vulcan:')
        elif player_choice == 'dynamite' or player_choice == 'tnt':
            await ctx.send(bot_choice_message)
            await ctx.send('No wait that\'s cheati.. :fire: :fire: :fire:')
        elif player_choice == 'lizard':
            await ctx.send(':lizard:')
        else:
            await ctx.send('Wait, that\'s not a valid move!')


def setup(client):
    client.add_cog(Minigames(client))
