import os
import json
from dotenv import load_dotenv

import discord
from discord.ext import commands

load_dotenv()

class Core(commands.Cog):

    def __init__(self, client):
        self.client = client
        with open('data/variables.json', 'r') as file:
            self.variables = json.load(file)

    #Event listeners
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(status=discord.Status.idle, activity=discord.Game("I'm sorry dave, I can't do that."))
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

    @commands.Cog.listener()
    async def on_message(self, message):
        # Is a dm to the bot (A. verification, B. Modmail)
        if message.guild is None and message.author != self.client.user:
            # DM is a command
            if message.content[0] == '!':
                if message.author.id not in self.variables.get('allowed_user_ids'):
                    await message.author.send('You do not have the permissions to use this command.')
                return

            with open('data/users.json', 'r') as file:
                user_db = json.load(file)

            if message.author.id in user_db:  # TODO: implement modmail
                    msg = "What server would you like to send this modmail to?"
                    await message.author.send()


            else:  # Is verification, pass to method
                from cogs.verification import Verification
                await Verification.step_2_verify(Verification(self.client), message.author, message.content)


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
    client.add_cog(Core(client))