import random

import discord
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


    @commands.command(usage='minesweeper <columns> <rows> <bombs>', description='A game of minesweeper')
    async def minesweeper(self, ctx, columns=None, rows=None, bombs=None):
        errortxt = "That is not formatted properly or valid positive integers weren't used, the proper format is:" \
                   "\n`[Prefix]minesweeper <columns> <rows> <bombs>`\n\n" \
                   "You can give me nothing for random columns, rows, and bombs."

        if columns is None or rows is None and bombs is None:
            if columns is not None or rows is not None or bombs is not None:
                await ctx.send(errortxt)
                return
            else:
                # Gives a random range of columns and rows from 4-13 if no arguments are given
                # The amount of bombs depends on a random range from 5 to this formula:
                # ((columns * rows) - 1) / 2.5
                # This is to make sure the percentages of bombs at a given random board isn't too high
                columns = random.randint(4, 13)
                rows = random.randint(4, 13)
                bombs = columns * rows - 1
                bombs = bombs / 2.5
                bombs = round(random.randint(5, round(bombs)))
        try:
            columns = int(columns)
            rows = int(rows)
            bombs = int(bombs)
        except ValueError:
            await ctx.send(errortxt)
            return
        if columns > 13 or rows > 13:
            await ctx.send('The limit for the columns and rows are 13 due to discord limits...')
            return
        if columns < 1 or rows < 1 or bombs < 1:
            await ctx.send('The provided numbers cannot be zero or negative...')
            return
        if bombs + 1 > columns * rows:
            await ctx.send(':boom:**BOOM**, you have more bombs than spaces on the grid or you attempted to make all of the spaces bombs!')
            return

        # Creates a list within a list and fills them with 0s, this is our makeshift grid
        grid = [[0 for num in range(columns)] for num in range(rows)]

        # Loops for the amount of bombs there will be
        loop_count = 0
        while loop_count < bombs:
            x = random.randint(0, columns - 1)
            y = random.randint(0, rows - 1)
            # We use B as a variable to represent a Bomb (this will be replaced with emotes later)
            if grid[y][x] == 0:
                grid[y][x] = 'B'
                loop_count = loop_count + 1
            # It will loop again if a bomb is already selected at a random point
            if grid[y][x] == 'B':
                pass

        # The while loop will go though every point though our makeshift grid
        pos_x = 0
        pos_y = 0
        while pos_x * pos_y < columns * rows and pos_y < rows:
            # We need to predefine this for later
            adj_sum = 0
            # Checks the surrounding points of our "grid"
            for (adj_y, adj_x) in [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1)]:
                # There will be index errors, we can just simply ignore them by using a try and exception block
                try:
                    if grid[adj_y + pos_y][adj_x + pos_x] == 'B' and adj_y + pos_y > -1 and adj_x + pos_x > -1:
                        # adj_sum will go up by 1 if a surrounding point has a bomb
                        adj_sum = adj_sum + 1
                except Exception as error:
                    pass
            # Since we don't want to change the Bomb variable into a number,
            # the point that the loop is in will only change if it isn't "B"
            if grid[pos_y][pos_x] != 'B':
                grid[pos_y][pos_x] = adj_sum
            # Increases the X values until it is more than the columns
            # If the while loop does not have "pos_y < rows" will index error
            if pos_x == columns - 1:
                pos_x = 0
                pos_y = pos_y + 1
            else:
                pos_x = pos_x + 1

        # Builds the string to be Discord-ready
        string_builder = []
        for the_rows in grid:
            string_builder.append(''.join(map(str, the_rows)))
        string_builder = '\n'.join(string_builder)
        # Replaces the numbers and B for the respective emotes and spoiler tags
        string_builder = string_builder.replace('0', '||:zero:||')
        string_builder = string_builder.replace('1', '||:one:||')
        string_builder = string_builder.replace('2', '||:two:||')
        string_builder = string_builder.replace('3', '||:three:||')
        string_builder = string_builder.replace('4', '||:four:||')
        string_builder = string_builder.replace('5', '||:five:||')
        string_builder = string_builder.replace('6', '||:six:||')
        string_builder = string_builder.replace('7', '||:seven:||')
        string_builder = string_builder.replace('8', '||:eight:||')
        final = string_builder.replace('B', '||:bomb:||')

        percentage = columns * rows
        percentage = bombs / percentage
        percentage = 100 * percentage
        percentage = round(percentage, 2)

        embed = discord.Embed(title='\U0001F642 Minesweeper \U0001F635', color=0xC0C0C0)
        embed.add_field(name='Columns:', value=columns, inline=True)
        embed.add_field(name='Rows:', value=rows, inline=True)
        embed.add_field(name='Total Spaces:', value=columns * rows, inline=True)
        embed.add_field(name='\U0001F4A3 Count:', value=bombs, inline=True)
        embed.add_field(name='\U0001F4A3 Percentage:', value=f'{percentage}%', inline=True)
        embed.add_field(name='Requested by:', value=ctx.author.display_name, inline=True)
        await ctx.send(content=f'\U0000FEFF\n{final}', embed=embed)

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
