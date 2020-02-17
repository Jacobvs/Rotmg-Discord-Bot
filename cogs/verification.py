import json
from _contextvars import ContextVar

import discord
from discord.ext import commands


class Verification(commands.Cog):

    def __init__(self, client):
        self.client = client
        with open('data/variables.json', 'r') as file:
            variables = json.load(file)

        self.verify_message_id = variables.get('verify_message_id')
        if self.verify_message_id is None:
            self.verify_message_id = 0


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.client.user.id:
            return

        if payload.message_id == self.verify_message_id and str(payload.emoji) == '✅':
            user = self.client.get_guild(payload.guild_id).get_member(payload.user_id)

            embed = discord.Embed(
                title="Verification Status",
                color=discord.Color.teal()
            )
            if discord.utils.get(user.roles, name="Verified") is not None:
                embed.description = "__You are already verified!__"
                embed.add_field(name="Troubleshooting", value="If there are still missing channels, please contact a "
                                                              "moderator+!")
            else:
                with open('data/users.json', 'r') as file:
                    user_db = json.load(file)
                if payload.user_id in user_db:
                    if user_db[payload.user_id]["suspended"]["state"]:
                        embed.description = "**You are currently suspended from this server.**"
                else:
                    embed.description = "__You are not yet verified. Follow the steps below to gain access to the " \
                                        "server.__ "
                    embed.add_field(name="\a", value="**Please provide your IGN** as it is spelled in-game.\nOnly "
                                                     "send your IGN, ex: `Darkmattr`\n\nCapitalization does not "
                                                     "matter.")

            await user.send(embed=embed)


    async def step_2_verify(self, user, ign):
        print("Step 2 verification")
        print(str(user.id))
        print("recieved IGN of: {}".format(ign))

        # TODO : implement TIFFIT API to do reverse lookup


    # TODO: add support for multiple servers w/ independent reqs
    @commands.command()
    async def add_verify_msg(self, ctx):
        embed = discord.Embed(
            title='Verification Steps',
            description="1. Enable DM's from server members\n2. Set **everything** to public except last known "
                        "location\n3. React to the ✅ below\n4. Follow all the directions the bot DM's you.",
            color=discord.Color.green()
        )
        embed.add_field(name="Troubleshooting", value="If you're having trouble verifying, post in #support!",
                        inline=False)

        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        with open('data/variables.json', 'r') as file:
            variables = json.load(file)

        variables['verify_message_id'] = message.id

        with open('data/variables.json', 'w') as file:
            json.dump(variables, file, indent=4)

        self.verify_message_id = message.id


def setup(client):
    client.add_cog(Verification(client))
