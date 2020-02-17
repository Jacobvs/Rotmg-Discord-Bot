import json
import random
import string
from threading import Timer

import requests

import discord
from discord.ext import commands


class Verification(commands.Cog):

    def __init__(self, client):
        self.client = client

    async def load_user_data(self):
        with open('data/users.json', 'r') as file:
            return json.load(file)

    async def write_user_data(self, data):
        with open('data/users.json', 'w') as file:
            json.dump(data, file, indent=4)

    async def load_guild_data(self):
        with open('data/guilds.json', 'r') as file:
            return json.load(file)

    async def write_guild_data(self, data):
        with open('data/guilds.json', 'w') as file:
            json.dump(data, file, indent=4)


    async def step_1_verify(self, user, ign):
        user_db = await self.load_user_data()

        embed = discord.Embed(
            title="Verification Status",
            description="Is `{}` the correct username?".format(ign),
            color=discord.Color.teal()
        )
        embed.add_field(name='https://www.realmeye.com/player/{}'.format(ign),
                        value="React with the check if so, x to cancel")
        msg = await user.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        user_db[str(user.id)].update({"ign": ign, "status": "stp_2", "verify_id": int(msg.id)})
        await self.write_user_data(user_db)

    async def step_2_verify(self, user_id):
        user = self.client.get_user(user_id)
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        user_db = await self.load_user_data()
        message = await user.fetch_message(user_db[str(user_id)]['verify_id'])
        embed = discord.Embed(
            title="You're almost done!",
            description="You have chosen `{}` to be your IGN.".format(user_db[str(user_id)]["ign"]),
            color=discord.Color.teal()
        )
        embed.add_field(name="\a",
                        value="Please paste the code below into any line of your [realmeye](https://www.realmeye.com/player/{}) description."
                              "\n```{}```\n\nOnce you are done, un-react to the check emoji and re-react to finish!".format(
                            user_db[str(user_id)]["ign"], key))
        await message.edit(embed=embed)
        user_db[str(user_id)].update({"verify_key": key, "status": "stp_3"})
        await self.write_user_data(user_db)

    async def step_3_verify(self, user_id, reverify):
        user_db = await self.load_user_data()
        guild_db = await self.load_guild_data()
        guild_db = guild_db[user_db[str(user_id)]["verify_guild"]]
        fame_req = int(guild_db["fame_req"])
        n_maxed_req = int(guild_db["n_maxed"])
        req_both = str(guild_db["req_both"])=="yes"
        guild = self.client.get_guild(int(guild_db["id"]))
        member = guild.get_member(user_id)

        embed = discord.Embed(
            title="Retrieving data from Realmeye...",
            color=discord.Color.green()
        )
        msg = await member.send(embed=embed)
        data = requests.get('https://nightfirec.at/realmeye-api/?player={}'.format(user_db[str(user_id)]["ign"])).json()
        alive_fame = 0
        n_maxed = 0
        name = str(data["player"])
        for char in data["characters"]:
            alive_fame += int(char["fame"])
            if int(char["stats_maxed"]) == 8:
                n_maxed += 1
        await msg.delete()
        description = data["desc1"] + data["desc2"] + data["desc3"]
        if reverify or user_db[str(user_id)]["verify_key"] in description:
            if (alive_fame >= fame_req or not req_both) and (n_maxed >= n_maxed_req or not req_both) and (alive_fame >= fame_req or n_maxed >= n_maxed_req):
                role = discord.utils.get(guild.roles, id=int(guild_db["verified_role_id"]))
                try:
                    await member.add_roles(role)
                    await member.edit(nick=name)
                except discord.errors.Forbidden:
                    print("Missing permissions for: {} in guild: {}".format(member.name, guild.name))
                message = await member.fetch_message(user_db[str(user_id)]['verify_id'])
                embed = discord.Embed(
                    title="Success!",
                    description="You are now a verified member of __{}__!".format(guild.name),
                    color=discord.Color.green()
                )
                await message.edit(embed=embed)
                guilds = list(user_db[str(user_id)].get("verified_guilds"))
                guilds.append(guild.name)
                user_db[str(user_id)].update({"status":"verified", "verified_guilds": guilds, "ign":name})
                if not reverify:
                    del user_db[str(user_id)]["verify_key"]
                del user_db[str(user_id)]["verify_id"]
                del user_db[str(user_id)]["verify_guild"]
                await self.write_user_data(user_db)
            else:

                await member.send("Sorry , you do not meet")  # TODO: implement and appeal
        else:
            embed = discord.Embed(
                title="Error!",
                description="You do not appear to have the code in your description.",
                color=discord.Color.red()
            )
            embed.add_field(name="\a",
                            value="If you have already placed the code in your description, wait a minute for the servers to catch up and re-react to the check above.")
            msg = await member.send(embed=embed)
            Timer(10, await msg.delete()).start()


    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.client.user.id:
            return

        user_db = await self.load_user_data()

        if payload.guild_id is not None:
            guild_db = await self.load_guild_data()
            guild = self.client.get_guild(payload.guild_id)
            verify_message_id = guild_db[str(guild.name)]["verification_id"]

            if payload.message_id == verify_message_id and str(payload.emoji) == '✅':
                user = guild.get_member(payload.user_id)

                embed = discord.Embed(
                    title="Verification Status",
                    color=discord.Color.teal()
                )
                if str(payload.user_id) in user_db.keys():
                    if guild.name in user_db[str(payload.user_id)]["verified_guilds"]:
                        verified = True
                        embed.description = "__You are already verified!__"
                        embed.add_field(name="Troubleshooting",
                                        value="If there are still missing channels, please contact a "
                                              "moderator+!")
                    elif user_db[str(payload.user_id)]["status"] == "verified":
                        embed.description = "__You have been verified in another server__"
                        embed.add_field(name="Verified Servers:", value='`{}`'.format(user_db[str(payload.user_id)]["verified_guilds"]))
                        embed.add_field(name="\a", value="React with a thumbs up if you would like to verify for this server with the IGN: `{}`.".format(user_db[str(payload.user_id)]["ign"]),inline=False)
                        msg = await user.send(embed=embed)
                        await msg.add_reaction('👍')
                        user_db[str(user.id)].update({"verify_id":msg.id, "verify_guild": guild.name})
                        await self.write_user_data(user_db)
                        return

                #elif discord.utils.get(user.roles, name="Verified") is not None:

                else:
                    verified = False
                    embed.description = "__You are not yet verified. Follow the steps below to gain access to the " \
                                            "server.__ "
                    embed.add_field(name="\a", value="**Please provide your IGN** as it is spelled in-game.\nOnly "
                                                         "send your IGN, ex: `Darkmattr`\n\nCapitalization does not "
                                                         "matter.")
                    embed.set_footer(text="React to the 'X' to cancel verification.")

                msg = await user.send(embed=embed)
                if not verified:
                    if str(user.id) in user_db.keys():
                        user_db[str(user.id)].update({"status": "stp_1", "verify_guild": guild.name, "verify_id": msg.id})
                    else:
                        user_db.update({user.id: {"status": "stp_1", "verify_guild": guild.name, "verify_id": msg.id, "verified_guilds":[]}})
                    await msg.add_reaction('❌')

                await self.write_user_data(user_db)

        if str(payload.user_id) in user_db.keys():
            if payload.message_id == user_db[str(payload.user_id)]['verify_id']:
                if str(payload.emoji) == '✅':
                    status = user_db[str(payload.user_id)]["status"]
                    if status == "stp_2":
                        await self.step_2_verify(payload.user_id)
                        return
                    elif status == "stp_3":
                        await self.step_3_verify(payload.user_id, reverify=False)
                        return
                elif str(payload.emoji) == '❌':
                    embed = discord.Embed(
                        title="Verification Cancelled.",
                        description="You have cancelled the verification process.\nIf you would like to restart, re-react to the verification message in the server.",
                        color=discord.Color.red()
                    )
                    user = self.client.get_user(payload.user_id)
                    message = await user.fetch_message(user_db[str(payload.user_id)]['verify_id'])
                    await message.edit(embed=embed)
                    user_db.pop(str(payload.user_id))
                    await self.write_user_data(user_db)
                elif str(payload.emoji) == '👍':
                    await self.step_3_verify(payload.user_id, reverify=True)



    # TODO: add support for multiple servers w/ independent reqs
    @commands.command()
    async def add_verify_msg(self, ctx):
        """Add the verification message to channel"""

        if ctx.guild is None:
            await ctx.send("This command must be used in a server.")

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
        guilds = await self.load_guild_data()

        guilds[ctx.guild.name].update({"verification_id": message.id})

        await self.write_guild_data(guilds)


def setup(client):
    client.add_cog(Verification(client))
