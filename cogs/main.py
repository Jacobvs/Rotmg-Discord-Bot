import os
import json
from dotenv import load_dotenv

import discord
from discord.ext import commands

load_dotenv()

class Main(commands.Cog):

    def __init__(self, client):
        self.client = client

    #Event listeners
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(status=discord.Status.idle, activity=discord.Game('What is my purpose?'))
        print(f'{self.client.user.name} has connected to Discord!')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        prefixes[str(guild.id)] = '!'

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        prefixes.pop(str(guild.id))

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)


    #Error Handlers
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send('Please pass in all the required arguments for this command')
        if isinstance(error, commands.CommandNotFound):
            await ctx.send('Invalid command. Use !help to see all of the available commands.')

    @commands.Cog.listener()
    async def on_error(self, event, *args, **kwargs):
        with open('err.log', 'a') as f:
            if event == 'on_message':
                f.write(f'Unhandled message: {args[0]}\n')
            else:
                raise


def setup(client):
    client.add_cog(Main(client))