import json
import discord
from discord.ext import commands

import sql


class Core(commands.Cog):

    def __init__(self, client):
        self.client = client
        with open('data/variables.json', 'r') as file:
            self.variables = json.load(file)

    #Event listeners
    @commands.Cog.listener()
    async def on_ready(self):
        await self.client.change_presence(status=discord.Status.online, activity=discord.Game("I'm sorry dave, I can't do that."))
        print(f'{self.client.user.name} has connected to Discord!')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        #
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)
        prefixes.update({guild.id: '!'})
        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        sql.add_new_guild(guild.id, guild.name)

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)
        prefixes.pop(str(guild.id))
        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        # TODO: Remove guilds and user-data from sql

    @commands.Cog.listener()
    async def on_message(self, message):
        # Is a dm to the bot (A. verification, B. Mod-mail)
        if message.guild is None and message.author != self.client.user:
            # DM is a command
            if message.content[0] == '!':
                # TODO: implement proper checks
                if message.author.id not in self.variables.get('allowed_user_ids'):
                    await message.author.send('You do not have the permissions to use this command.')
                return

            user_data = sql.get_user(message.author.id)

            if user_data is not None:  # TODO: implement modmail & check to ensure not verifying
                if user_data[sql.usr_cols.status] == 'verified':
                    msg = "What server would you like to send this modmail to?"
                    await message.author.send(msg)
                    return
                elif user_data[sql.usr_cols.status] == 'stp_1':
                    from cogs.verification import Verification
                    await Verification.step_1_verify(Verification(self.client), message.author, message.content)
                else:
                    await message.author.send("You are already verifying, react to the check to continue.", delete_after=10)


def setup(client):
    client.add_cog(Core(client))