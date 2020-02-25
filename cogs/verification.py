import random
import string
import embeds
import sql

import requests

import discord
from discord.ext import commands


class Verification(commands.Cog):
    "Verification Commands"

    def __init__(self, client):
        self.client = client

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
        star_req = guild_data[sql.gld_cols.nstars]
        req_all = guild_data[sql.gld_cols.reqall]
        private_loc = guild_data[sql.gld_cols.privateloc]

        embed = embeds.verification_checking_realmeye()
        msg = await member.send(embed=embed)
        data = requests.get('https://nightfirec.at/realmeye-api/?player={}'.format(user_data[sql.usr_cols.ign])).json()
        if 'error' in data.keys():
            embed = embeds.verification_bad_username()
            await member.send(embed=embed, delete_after=10)
            sql.update_user(user_id, "status", "stp_1")
            embed = embeds.verification_dm_start()
            message = await member.fetch_message(user_data[sql.usr_cols.verifyid])
            await message.edit(embed=embed)
            return
        alive_fame = 0
        n_maxed = 0
        name = str(data["player"])
        n_stars = int(data["rank"])
        location = data["player_last_seen"]
        for char in data["characters"]:
            alive_fame += int(char["fame"])
            if int(char["stats_maxed"]) == 8:
                n_maxed += 1
        await msg.delete()
        description = data["desc1"] + data["desc2"] + data["desc3"]

        channel = self.client.get_channel(guild_data[sql.gld_cols.verifylogchannel])
        if reverify or user_data[sql.usr_cols.verifykey] in description:
            if not private_loc or location == "hidden":
                verified = False
                if req_all:
                    if alive_fame >= fame_req and n_maxed >= n_maxed_req and n_stars >= star_req:
                        verified = True
                else:
                    if alive_fame >= fame_req or n_maxed >= n_maxed_req or n_stars >= star_req:
                        verified = True
                if verified:
                    await complete_verification(guild, guild_data, member, name, user_data, reverify)
                    await channel.send(f"{member.mention} has completed verification.")
                else:
                    embed = embeds.verification_bad_reqs(guild_data[sql.gld_cols.reqsmsg])
                    sql.update_user(user_id, "status", "denied")
                    sql.update_user(user_id, "ign", name)
                    message = await member.fetch_message(user_data[sql.usr_cols.verifyid])
                    await message.edit(embed=embed)
                    await channel.send(f"{member.mention} does not meet requirements.")
            else:
                embed = embeds.verification_public_location()
                await member.send(embed=embed, delete_after=10)
        else:
            embed = embeds.verification_missing_code()
            await member.send(embed=embed, delete_after=10)
            await channel.send(f"{member.mention} is missing their realmeye code (or api is down).")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.client.user.id:
            return

        user_data = sql.get_user(payload.user_id)
        user = self.client.get_user(payload.user_id)

        if payload.guild_id is not None:
            guild = self.client.get_guild(payload.guild_id)
            guild_data = sql.get_guild(guild.id)
            verify_message_id = guild_data[sql.gld_cols.verificationid]
            verified = False

            if payload.message_id == verify_message_id and str(payload.emoji) == '✅':
                vfy_msg = await self.client.get_channel(payload.channel_id).fetch_message(verify_message_id)
                await vfy_msg.remove_reaction('✅', user)

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
                            channel = self.client.get_channel(guild_data[sql.gld_cols.verifylogchannel])
                            await channel.send(f"{user.mention} is re-verifying for this guild.")
                            return
                    elif user_data[sql.usr_cols.status] == "denied":
                        embed = embeds.verification_bad_reqs(guild_data[sql.gld_cols.reqsmsg])
                        msg = await user.send(embed=embed)
                        msg.add_reaction('✅')
                        sql.update_user(payload.user_id, "verifyid", msg.id)
                    elif user_data[sql.usr_cols.status] == "deny_appeal":
                        await user.send("Your application is being reviewed by staff. Please wait for their decision.")
                    else:
                        embed = embeds.verification_dm_start()
                        channel = self.client.get_channel(guild_data[sql.gld_cols.verifylogchannel])
                        await channel.send(f"{user.mention} has started the verification process.")
                        msg = await user.send(embed=embed)

                else:
                    embed = embeds.verification_dm_start()
                    channel = self.client.get_channel(guild_data[sql.gld_cols.verifylogchannel])
                    await channel.send(f"{user.mention} has started the verification process.")
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
                if user_data[sql.usr_cols.status] != "denied":
                    if user_data[sql.usr_cols.status] != "cancelled":
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
                            message = await user.fetch_message(user_data[sql.usr_cols.verifyid])
                            await message.edit(embed=embed)
                            channel = self.client.get_channel(sql.get_guild(user_data[sql.usr_cols.verifyguild])[sql.gld_cols.verifylogchannel]) #unknown colum none in where clause
                            await channel.send(f"{user.mention} has cancelled the verification process.")
                            sql.update_user(payload.user_id, "verifyguild", None)
                            sql.update_user(payload.user_id, "status", "cancelled")
                        elif str(payload.emoji) == '👍':
                            await self.step_3_verify(payload.user_id, reverify=True)
                else:
                    if str(payload.emoji) == '✅' or str(payload.emoji) == '👍':
                        guild_data = sql.get_guild(user_data[sql.usr_cols.verifyguild])
                        guild = self.client.get_guild(guild_data[sql.gld_cols.id])
                        channel = guild.get_channel(guild_data[sql.gld_cols.manualverifychannel])
                        msg = await channel.send(embed=embeds.verification_manual_verify(user.mention, user_data[sql.usr_cols.ign], payload.user_id, user_data[sql.usr_cols.verifykey]))
                        sql.update_user(payload.user_id, "status", "deny_appeal")
                        sql.update_user(payload.user_id, "verifyid", msg.id)
                        await user.send("Your application is being reviewed by staff. Please wait for their decision.")
                    elif str(payload.emoji) == '❌':
                        embed = embeds.verification_cancelled()
                        await user.send(embed=embed)
                        sql.update_user(payload.user_id, "verifyguild", None)
                        sql.update_user(payload.user_id, "verifyid", None)
                        sql.update_user(payload.user_id, "status", "cancelled")

    # TODO: add support for multiple servers w/ independent reqs
    @commands.command(usage="!add_verify_msg")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def add_verify_msg(self, ctx):
        """Add the verification message to channel"""

        guild_db = sql.get_guild(ctx.guild.id)
        embed = embeds.verification_check_msg(guild_db[sql.gld_cols.reqsmsg], guild_db[sql.gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        sql.update_guild(ctx.guild.id, "verificationid", message.id)


def setup(client):
    client.add_cog(Verification(client))


async def step_1_verify(user, ign):
    embed = embeds.verification_step_1(ign)
    msg = await user.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    sql.update_user(user.id, "ign", ign)
    sql.update_user(user.id, "status", "stp_2")
    sql.update_user(user.id, "verifyid", msg.id)

async def complete_verification(guild, guild_data, member, name, user_data, reverify):
    role = discord.utils.get(guild.roles, id=guild_data[sql.gld_cols.verifiedroleid])
    try:
        await member.add_roles(role)
        await member.edit(nick=name)
    except discord.errors.Forbidden:
        print("Missing permissions for: {} in guild: {}".format(member.name, guild.name))

    embed = embeds.verification_success(guild.name, member.mention)
    await member.send(embed=embed)
    guilds = user_data[sql.usr_cols.verifiedguilds]
    if guilds is None:
        guilds = []
    else:
        guilds = guilds.split(",")
    guilds.append(guild.name)
    sql.update_user(member.id, "status", "verified")
    sql.update_user(member.id, "verifiedguilds", ','.join(guilds))
    if not reverify:
        sql.update_user(member.id, "ign", name)
    sql.update_user(member.id, "verifykey", None)
    sql.update_user(member.id, "verifyid", None)
    sql.update_user(member.id, "verifyguild", None)