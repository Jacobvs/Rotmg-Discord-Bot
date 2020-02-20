import asyncio
import json
import random
import string
import embeds
import sql

import requests

import discord
from discord.ext import commands


class Verification(commands.Cog):

    def __init__(self, client):
        self.client = client

    async def step_1_verify(self, user, ign):
        embed = embeds.verification_step_1(ign)
        msg = await user.send(embed=embed)
        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        sql.update_user(user.id, "ign", ign)
        sql.update_user(user.id, "status", "stp_2")
        sql.update_user(user.id, "verifyid", msg.id)

    async def step_2_verify(self, user_id):
        user = self.client.get_user(user_id)
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        user_data = sql.get_user(user_id)
        message = await user.fetch_message(user_data[sql.usr_cols.verifyid])
        embed = embeds.verification_step_2(user_data[sql.usr_cols.ign], key)
        await message.edit(embed=embed)
        sql.update_user(user_id, "verifykey", key)
        sql.update_user(user_id, "status", "stp_3")

    async def step_3_verify(self, user_id, reverify):
        user_data = sql.get_user(user_id)
        guild = self.client.get_guild(user_data[sql.usr_cols.verifyguild])
        member = guild.get_member(user_id)
        guild_data = sql.get_guild(guild.id)

        fame_req = guild_data[sql.gld_cols.nfame]
        n_maxed_req = guild_data[sql.gld_cols.nmaxed]
        req_both = guild_data[sql.gld_cols.reqboth]

        embed = embeds.verification_checking_realmeye()
        msg = await member.send(embed=embed)
        data = requests.get('https://nightfirec.at/realmeye-api/?player={}'.format(user_data[sql.usr_cols.ign])).json()
        alive_fame = 0
        n_maxed = 0
        name = str(data["player"])
        for char in data["characters"]:
            alive_fame += int(char["fame"])
            if int(char["stats_maxed"]) == 8:
                n_maxed += 1
        await msg.delete()
        description = data["desc1"] + data["desc2"] + data["desc3"]

        if reverify or user_data[sql.usr_cols.verifykey] in description:
            message = await member.fetch_message(user_data[sql.usr_cols.verifyid])
            if (alive_fame >= fame_req or not req_both) and (n_maxed >= n_maxed_req or not req_both) and (
                    alive_fame >= fame_req or n_maxed >= n_maxed_req):
                role = discord.utils.get(guild.roles, id=guild_data[sql.gld_cols.verifiedroleid])
                try:
                    await member.add_roles(role)
                    await member.edit(nick=name)
                except discord.errors.Forbidden:
                    print("Missing permissions for: {} in guild: {}".format(member.name, guild.name))

                embed = embeds.verification_success(guild.name)
                await message.edit(embed=embed)
                guilds = user_data[sql.usr_cols.verifiedguilds]
                if guilds is None:
                    guilds = []
                else:
                    guilds = guilds.split(",")
                guilds.append(guild.name)
                sql.update_user(user_id, "status", "verified")
                sql.update_user(user_id, "verifiedguilds", ','.join(guilds))
                sql.update_user(user_id, "ign", name)
                if not reverify:
                    sql.update_user(user_id, "verifykey", None)

                sql.update_user(user_id, "verifyid", None)
                sql.update_user(user_id, "verifyguild", None)
            else:
                embed = embeds.verification_bad_reqs(guild_data[sql.gld_cols.reqsmsg])
                sql.update_user(user_id, "status", "denied")
                sql.update_user(user_id, "ign", name)
                sql.update_user(user_id, "verifykey", None)

                await message.edit(embed=embed)
        else:
            embed = embeds.verification_missing_code()
            await member.send(embed=embed, delete_after=10)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.client.user.id:
            return

        user_data = sql.get_user(payload.user_id)

        if payload.guild_id is not None:
            guild = self.client.get_guild(payload.guild_id)
            guild_data = sql.get_guild(guild.id)
            verify_message_id = guild_data[sql.gld_cols.verificationid]
            verified = False

            if payload.message_id == verify_message_id and str(payload.emoji) == '✅':
                user = guild.get_member(payload.user_id)
                msg = await self.client.get_channel(payload.channel_id).fetch_message(verify_message_id)
                await msg.remove_reaction('✅', user)

                if user_data is not None:
                    verified_guilds = user_data[sql.usr_cols.verifiedguilds]
                    if verified_guilds is not None:
                        verified_guilds = verified_guilds.split(",")
                        if guild.name in verified_guilds:
                            verified = True
                            embed = embeds.verification_already_verified()
                            msg = await user.send(embed=embed)
                        else:
                            embed = embeds.verification_already_verified_complete(verified_guilds,
                                                                                  user_data[sql.usr_cols.ign])
                            msg = await user.send(embed=embed)
                            await msg.add_reaction('👍')
                            await msg.add_reaction('❌')  # TODO: test cancel
                            sql.update_user(user.id, "verifyid", msg.id)
                            sql.update_user(user.id, "verifyguild", guild.id)
                            return

                else:
                    embed = embeds.verification_dm_start()
                    msg = await user.send(embed=embed)

                if user_data is None:
                    sql.add_new_user(payload.user_id, guild.id, msg.id)
                else:
                    sql.update_user(payload.user_id, "verifyguild", guild.id)
                    sql.update_user(payload.user_id, "verifyid", msg.id)
                if not verified:
                    await msg.add_reaction('❌')

        elif user_data is not None:
            if payload.message_id == user_data[sql.usr_cols.verifyid]:
                if str(payload.emoji) == '✅':
                    status = user_data[sql.usr_cols.status]
                    if status == 'stp_2':
                        await self.step_2_verify(payload.user_id)
                        return
                    elif status == 'stp_3':
                        await self.step_3_verify(payload.user_id, reverify=False)
                        return
                elif str(payload.emoji) == '❌':
                    embed = embeds.verification_cancelled()
                    user = self.client.get_user(payload.user_id)
                    message = await user.fetch_message(user_data[sql.usr_cols.verifyid])
                    await message.edit(embed=embed)
                    sql.update_user(payload.user_id, "verifyguild", None)
                    sql.update_user(payload.user_id, "status", "stp_1")
                elif str(payload.emoji) == '👍':
                    await self.step_3_verify(payload.user_id, reverify=True)

    # TODO: add support for multiple servers w/ independent reqs
    @commands.command()
    async def add_verify_msg(self, ctx):
        """Add the verification message to channel"""

        if ctx.guild is None:
            await ctx.send("This command must be used in a server.")

        embed = embeds.verification_check_msg()
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        sql.update_guild(ctx.guild.id, "verificationid", message.id)


def setup(client):
    client.add_cog(Verification(client))
