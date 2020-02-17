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
        await self.client.change_presence(status=discord.Status.online, activity=discord.Game("I'm sorry dave, I can't do that."))
        print(f'{self.client.user.name} has connected to Discord!')

    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        with open('data/guilds.json', 'r') as file:
            guilds = json.load(file)

        prefixes.update({guild.id: '!'})
        guilds.update({guild.name:{"id":guild.id, "fame_req":0, "n_maxed":0,"verified_role_id":0}})

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        with open('data/guilds.json', 'w') as file:
            json.dump(guilds, file, indent=4)

    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        with open('data/guilds.json', 'r') as file:
            guilds = json.load(file)

        prefixes.pop(str(guild.id))
        guilds.pop(guild.name)

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        with open('data/guilds.json', 'w') as file:
            json.dump(guilds, file, indent=4)

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

            if str(message.author.id) in user_db:  # TODO: implement modmail & check to ensure not verifying
                if user_db[str(message.author.id)]['status'] == 'verified':
                    msg = "What server would you like to send this modmail to?"
                    await message.author.send(msg)
                    return

            # Is verification, pass to method
            if str(message.author.id) in user_db.keys():
                if user_db[str(message.author.id)]["status"] == "stp_1":
                    from cogs.verification import Verification
                    await Verification.step_1_verify(Verification(self.client), message.author, message.content)
                else:
                    msg = await message.author.send("You are already verifying, react to the check to continue.")


def setup(client):
    client.add_cog(Core(client))