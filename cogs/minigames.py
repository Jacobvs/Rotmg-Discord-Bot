import numpy as np
import discord
from discord.ext import commands

from cogs.Minigames.connect4 import Connect4
from cogs.Minigames.hangman import Hangman
from cogs.Minigames.highlow import HighLow
from cogs.Minigames.tictactoe import TicTacToe


class Minigames(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(usage="!connect4 [member]")
    async def connect4(self, ctx, other_player: discord.Member):
        """A game of Connect-4 with another member.
        Each player takes turn in placing a token on the board,
        the winner is the first to put four tokens in a row.
        """
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument('Cannot play a game against that member.')

        game = Connect4(ctx, self.client, other_player)
        await game.play()


    @commands.command(usage="!hangman")
    async def hangman(self, ctx):
        """A game of Hangman with a random word.
        You guess letters by typing them in chat.
        """
        game = Hangman(ctx, self.client)
        await game.play()


    @commands.command(usage="!highlow", name='higherlower', aliases=['highlow', 'hilo'])
    async def higher_lower(self, ctx):
        """A game of Higher-or-Lower.
        The player plays against the dealer (bot) for half a deck of cards.
        """
        game = HighLow(ctx, self.client)
        await game.play()


    @commands.command(usage="!tictactoe [member]", name='tictactoe')
    async def tic_tac_toe(self, ctx, other_player: discord.Member = None):
        """A game of Tic-Tac-Toe with another member.
        """
        if other_player.bot or other_player == ctx.author:
            raise commands.BadArgument('Cannot play a game against that member.')

        game = TicTacToe(ctx, self.client, other_player)
        await game.play()


    @commands.command(usage="!rps [choice]", name='rps', aliases=['rockpaperscissors'])
    async def rock_paper_scissors(self, ctx, player_choice=''):
        """Play a game of Rock Paper Scissors.
        """
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
