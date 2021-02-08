import json
import logging
import random
import string

import aiohttp
import discord
from discord.ext import commands

import checks
import embeds
import sql
import utils
from sql import get_guild, get_user, update_user, ign_exists, update_guild, add_new_user, usr_cols, gld_cols


class Verification(commands.Cog):
    """"Verification Commands"""


    def __init__(self, client):
        self.client = client

    async def step_2_verify(self, user_id):
        user = self.client.get_user(user_id)
        key = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
        user_data = await get_user(self.client.pool, user_id)
        message = await user.fetch_message(user_data[usr_cols.verifyid])
        embed = embeds.verification_step_2(user_data[usr_cols.ign], key)
        await message.edit(embed=embed)
        await update_user(self.client.pool, user_id, "verifykey", key)
        guild_data = await get_guild(self.client.pool, user_data[usr_cols.verifyguild])
        channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
        await channel.send(f"{user.mention} is on step 3 of verification.")
        await update_user(self.client.pool, user_id, "status", "stp_3")


    async def step_3_verify(self, user_id, reverify):
        user_data = await get_user(self.client.pool, user_id)
        guild = self.client.get_guild(user_data[usr_cols.verifyguild])
        member = guild.get_member(user_id)
        guild_data = await get_guild(self.client.pool, guild.id)

        channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])

        fame_req = guild_data[gld_cols.nfame]
        n_maxed_req = guild_data[gld_cols.nmaxed]
        star_req = guild_data[gld_cols.nstars]
        months_req = guild_data[gld_cols.creationmonths]
        req_all = guild_data[gld_cols.reqall]
        private_loc = guild_data[gld_cols.privateloc]

        embed = embeds.verification_checking_realmeye()
        msg = await member.send(embed=embed)

        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://darkmattr.uc.r.appspot.com/?player={user_data[usr_cols.ign]}", ssl=False) as r:
                if r.status == 403:
                    print("ERROR: API ACCESS FORBIDDEN")
                    await channel.send(f"<@{self.client.owner_id}> ERROR: API ACCESS REVOKED!.")
                data = await r.json()  # returns dict

        if not data:
            await update_user(self.client.pool, user_id, "status", "stp_1")
            embed = embeds.verification_dm_start()
            await member.send(
                "There has been an issue with retrieving data from realmeye. Ensure your profile is public. If this problem persists contact the developer.")
            return await member.send(embed=embed)

        if 'error' in data.keys() or await ign_exists(self.client.pool, user_data[usr_cols.ign], user_id):
            embed = embeds.verification_bad_username()
            await member.send(embed=embed)
            await update_user(self.client.pool, user_id, "status", "stp_1")
            embed = embeds.verification_dm_start()
            message = await member.fetch_message(user_data[usr_cols.verifyid])
            await message.edit(embed=embed)
            return

        alive_fame = 0
        n_maxed = 0
        name = str(data["player"])
        n_stars = int(data["rank"])
        location = data["player_last_seen"]

        if data["characters_hidden"]:
            embed = embeds.verification_private_chars()
            await member.send(embed=embed)
            return await channel.send(f"{member.mention} has private characters")

        for char in data["characters"]:
            alive_fame += int(char["fame"])
            if int(char["stats_maxed"]) == 8:
                n_maxed += 1

        if data["fame"] and data["fame"] != "hidden":
            alive_fame = int(data["fame"])

        description = data["desc1"] + data["desc2"] + data["desc3"]

        time = ""
        if "created" in data:
            time = data["created"]
        elif "player_first_seen" in data:
            time = data["player_first_seen"]

        if time and time != "hidden":
            days = 0
            if "years" in time:
                days += int(time.split(" years")[0].split("~")[1]) * 365
                if "days" in time:
                    days += int(time.split("and ")[1].split(" days")[0])
                elif 'day' in time:
                    days += 1
            elif "year" in time:
                days += int(time.split(" year")[0].split("~")[1]) * 365
                if "days" in time:
                    days += int(time.split("and ")[1].split(" days")[0])
                elif 'day' in time:
                    days += 1
            elif "days" in time:
                days += int(time.split(" days")[0].split("~")[1])
            months = days / 30
        else:
            embed = embeds.verification_private_time()
            await member.send(embed=embed)
            return await channel.send(f"{member.mention} has hidden their account creation date.")

        fame_passed = alive_fame >= fame_req
        maxed_passed = True  # TODO: Fix this! n_maxed >= n_maxed_req
        stars_passed = n_stars >= star_req
        months_passed = months >= months_req
        private_passed = not private_loc or location == "hidden"

        try:
            await msg.delete()
        except discord.errors.DiscordException:
            print("Unable to delete checking realmeye message")

        if reverify or user_data[usr_cols.verifykey] in description:
            if private_passed:
                verified = False
                if req_all:
                    if fame_passed and maxed_passed and stars_passed and months_passed:
                        verified = True
                else:
                    if fame_passed or maxed_passed or stars_passed or months_passed:
                        verified = True
                if verified:
                    await complete_verification(self.client.pool, guild, guild_data, member, name, user_data, reverify,
                                                user_data[usr_cols.alt1], user_data[usr_cols.alt2])
                    await channel.send(f"{member.mention} has completed verification.")
                else:
                    embed = embeds.verification_bad_reqs(guild_data[gld_cols.reqsmsg], fame_passed, maxed_passed, stars_passed,
                                                         months_passed, private_passed)
                    await update_user(self.client.pool, user_id, "status", "denied")
                    await update_user(self.client.pool, user_id, "ign", name)
                    message = await member.fetch_message(user_data[usr_cols.verifyid])
                    await message.edit(embed=embed)
                    await channel.send(f"{member.mention} does not meet requirements.")

            else:
                embed = embeds.verification_public_location()
                await member.send(embed=embed)
        else:
            embed = embeds.verification_missing_code(user_data[usr_cols.verifykey])
            await member.send(embed=embed)
            await channel.send(f"{member.mention} is missing their realmeye code (or api is down).")


    @commands.command(usage="addverimsg", description="Add the verification message to channel.")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def addverimsg(self, ctx):
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        embed = embeds.verification_check_msg(guild_db[gld_cols.reqsmsg], guild_db[gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        # Save verification message id for later to check reacts with
        await update_guild(self.client.pool, ctx.guild.id, "verificationid", message.id)


    @commands.command(usage="add_first_subverify", description="Add the first sub-verification message to channel.")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_first_subverify(self, ctx):
        await subverify_helper(self, ctx, 1)


    @commands.command(usage="add_second_subverify", description="Add the second sub-verification message to channel.")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_second_subverify(self, ctx):
        await subverify_helper(self, ctx, 2)

    @commands.command(usage='vetveri <member>', description='Veteran Verify a member')
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def vetveri(self, ctx, member: utils.MemberLookupConverter):
        vrole = self.client.guild_db[ctx.guild.id][sql.gld_cols.vetroleid]
        rrole = self.client.guild_db[ctx.guild.id][sql.gld_cols.raiderroleid]
        if not vrole:
            return await ctx.send("This server does not have a vet role configured yet!")

        if rrole not in member.roles:
            return await ctx.send("The specified member has not been verified in the primary section yet!")

        if vrole in member.roles:
            return await ctx.send("This member has already been veteran verified!")

        try:
            await member.add_roles(vrole)
        except discord.Forbidden:
            return await ctx.send("The bot does not have permission to add roles to the specified member!")
        except discord.HTTPException:
            return await ctx.send("An HTTP Error occured! Please try running the command again!")

        embed = discord.Embed(title="Veteran Verified!", description=f"You have been manually verified for the veteran section of:\n**__{ctx.guild.name}__**!\n\n"
                                                                     f"If this was a mistake, please contact a security+!", color=discord.Color.green())
        try:
            await member.send(embed=embed)
        except discord.Forbidden or discord.HTTPException:
            pass

        embed = discord.Embed(title="Success!", description=f"{member.display_name} has been manually __vet verified__!", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='addvetverimsg', description='Adds the veteran verification message to the current channel.')
    async def addvetverimsg(self, ctx):
        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        embed = embeds.vet_verification_check_msg(guild_db[gld_cols.vetverimsg], guild_db[gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass

        # Save verification message id for later to check reacts with
        await update_guild(self.client.pool, ctx.guild.id, "vetveriid", message.id)


def setup(client):
    client.add_cog(Verification(client))


async def vet_veri_helper(client, member, guild, ign, veri_msg):
    await veri_msg.remove_reaction('✅', member)
    guild_db = client.guild_db[guild.id]
    vetrole = guild_db[sql.gld_cols.vetroleid]
    if vetrole in member.roles:
        embed = discord.Embed(title="Error!", description="You appear to already be vet verified in this server! "
                                                          "If this is a mistake, please contact a security+!", color=discord.Color.red())
        try:
            return await member.send(embed=embed)
        except discord.Forbidden:
            return

    with open('data/guild_variables.json') as file:
        reqs = json.load(file)

    if str(guild.id) in reqs:
        n_runs = reqs[str(guild.id)]['runs']
    else:
        n_runs = reqs['-1']['runs']

    stats_logged = await sql.get_log(client.pool, guild.id, member.id)

    if stats_logged[sql.log_cols.runsdone] >= n_runs:
        try:
            await member.add_roles(vetrole)
            await guild_db[sql.gld_cols.verifylogchannel].send(f"{member.mention} has been veteran verified ({stats_logged[sql.log_cols.runsdone]}/{n_runs} runs completed)!")
            await member.send(member.mention, embed=embeds.vet_verification_success(guild.name, member.mention))
        except discord.Forbidden or discord.HTTPException:
            return await member.send("An unexpected error occured while adding the vet role! Please contact a security+ to help you resolve this issue!")
    else:
        msg = await guild_db[sql.gld_cols.manualverifychannel].send(f"Veteran Manual Verification UID: {member.id}",
                                                                 embed=embeds.vet_manual_verify(member, ign, stats_logged[sql.log_cols.runsdone], n_runs,
                                                                                                stats_logged[sql.log_cols.pkey]))
        await member.send("Your veteran raider application is being reviewed by staff. Please wait for their decision.")
        await msg.add_reaction('✅')
        await msg.add_reaction('❌')


async def subverify_helper(self, ctx, n):
    guild_db = await get_guild(self.client.pool, ctx.guild.id)
    if n == 1:
        embed = embeds.subverify_msg(guild_db[gld_cols.subverify1name], guild_db[gld_cols.supportchannelname])
    else:
        embed = embeds.subverify_msg(guild_db[gld_cols.subverify2name], guild_db[gld_cols.supportchannelname])
    message = await ctx.send(embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")
    await ctx.message.delete()

    # Save verification message id for later to check reacts with
    await update_guild(self.client.pool, ctx.guild.id, f"subverify{n}id", message.id)


async def step_1_verify(pool, user, ign):
    embed = embeds.verification_step_1(ign)
    msg = await user.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    await update_user(pool, user.id, "ign", ign)
    await update_user(pool, user.id, "status", "stp_2")
    await update_user(pool, user.id, "verifyid", msg.id)


async def complete_verification(pool, guild, guild_data, member, name, user_data, reverify, alt1=None, alt2=None):
    role = discord.utils.get(guild.roles, id=guild_data[gld_cols.verifiedroleid])
    tag = member.name
    alts = ""
    if alt1:
        alts += f" | {alt1}"
    if alt2:
        alts += f" | {alt2}"

    tag += alts
    try:
        await member.add_roles(role)
        await member.edit(nick=name)
    except discord.errors.Forbidden:
        print("Missing permissions for: {} in guild: {}".format(member.name, guild.name))

    embed = embeds.verification_success(guild.name, member.mention)
    try:
        await member.send(embed=embed)
    except discord.Forbidden:
        pass
    guilds = user_data[usr_cols.verifiedguilds]
    if guilds is None:
        guilds = []
    else:
        guilds = guilds.split(",")
    guilds.append(guild.name)
    await update_user(pool, member.id, "status", "verified")
    await update_user(pool, member.id, "verifiedguilds", ','.join(guilds))
    if not reverify:
        await update_user(pool, member.id, "ign", name)
    await update_user(pool, member.id, "verifykey", None)
    await update_user(pool, member.id, "verifyid", None)
    await update_user(pool, member.id, "verifyguild", None)


async def guild_verify_react_handler(self, payload, user_data, guild_data, user, guild, verify_msg_id):
    verified = False
    vfy_msg = await self.client.get_channel(payload.channel_id).fetch_message(verify_msg_id)
    channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
    await vfy_msg.remove_reaction('✅', user)

    if user_data is not None:
        verified_guilds = user_data[usr_cols.verifiedguilds]
        status = user_data[usr_cols.status]
        if verified_guilds is not None:
            verified_guilds = verified_guilds.split(",")
            if guild.name in verified_guilds:
                try:
                    if status == "appeal_denied":
                        return await user.send(
                            "You have been denied from verifying in this server. Contact a moderator+ if you think this is a mistake.")
                    elif user_data[usr_cols.status] == "deny_appeal":
                        return await user.send(
                            "You do not meet the requirements of this server, appeal with the check above or contact a moderator+ if you "
                            "think this is a mistake.")
                except discord.Forbidden:
                    ch = self.client.get_channel(payload.channel_id)
                    await ch.send(
                        f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                        "process. Once you do, re-react to the check to continue.", delete_after=15)

                verified = True
                role = discord.utils.get(guild.roles, id=guild_data[gld_cols.verifiedroleid])
                tag = payload.member.name
                name = user_data[usr_cols.ign]
                try:
                    await payload.member.add_roles(role)
                    if tag.lower() == name.lower():
                        await payload.member.edit(nick=f"{name} .")
                    else:
                        await payload.member.edit(nick=name)
                except discord.errors.Forbidden:
                    await channel.send("Missing permissions for: {}".format(payload.member.mention, guild.name))
                    logging.warning("Missing permissions for: {} in guild: {}".format(payload.member.name, guild.name))
                embed = embeds.verification_already_verified()
                msg = await user.send(embed=embed)
            elif status == "cancelled":
                await update_user(self.client.pool, user.id, "status", "stp_1")
                embed = embeds.verification_dm_start()
                await channel.send(f"{user.mention} is re-verifying after cancelling.")
                try:
                    msg = await user.send(embed=embed)
                except discord.Forbidden:
                    ch = self.client.get_channel(payload.channel_id)
                    await ch.send(
                        f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                        "process. Once you do, re-react to the check to continue.", delete_after=15)
            else:
                embed = embeds.verification_already_verified_complete(verified_guilds, user_data[usr_cols.ign])
                try:
                    msg = await user.send(embed=embed)
                except discord.Forbidden:
                    ch = self.client.get_channel(payload.channel_id)
                    await ch.send(
                        f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                        "process. Once you do, re-react to the check to continue.", delete_after=15)
                await msg.add_reaction('👍')
                await msg.add_reaction('❌')
                await update_user(self.client.pool, user.id, "verifyid", msg.id)
                await update_user(self.client.pool, user.id, "status", "stp_3")
                await update_user(self.client.pool, user.id, "verifyguild", guild.id)
                await channel.send(f"{user.mention} is re-verifying with the bot for this guild.")
                return
        elif status == "denied":
            embed = discord.Embed(title="Re-verification", value="You were previously denied from verifying with the bot.\n"
                                                                 "React to the 👍 to continue verifying.", color=discord.Color.orange())
            await channel.send(f"{user.mention} is re-verifying after being denied.")
            try:
                msg = await user.send(embed=embed)
            except discord.Forbidden:
                ch = self.client.get_channel(payload.channel_id)
                await ch.send(f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                              "process. Once you do, re-react to the check to continue.", delete_after=15)
            await update_user(self.client.pool, user.id, "verifyguild", guild.id)
            await update_user(self.client.pool, user.id, "verifyid", msg.id)
            await update_user(self.client.pool, user.id, "status", "stp_3")
            await msg.add_reaction('👍')
            await msg.add_reaction('❌')
        elif status == "deny_appeal":
            await user.send("Your application is being reviewed by staff. Please wait for their decision.")
        elif status != "stp_2" and status != "stp_3":
            embed = embeds.verification_dm_start()
            await channel.send(f"{user.mention} has started the verification process.")
            try:
                msg = await user.send(embed=embed)
            except discord.Forbidden:
                ch = self.client.get_channel(payload.channel_id)
                await ch.send(f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                              "process. Once you do, re-react to the check to continue.", delete_after=15)
        else:
            try:
                await user.send("You have already started the verification process, scroll up to find the last message the bot sent "
                                "regarding verification and continue from there.")
            except discord.Forbidden:
                ch = self.client.get_channel(payload.channel_id)
                await ch.send(f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                              "process. Once you do, re-react to the check to continue.", delete_after=15)

    else:
        embed = embeds.verification_dm_start()
        await channel.send(f"{user.mention} has started the verification process.")
        try:
            msg = await user.send(embed=embed)
        except discord.Forbidden:
            ch = self.client.get_channel(payload.channel_id)
            await ch.send(f"{payload.member.mention} - You need to enable DM's from server members to continue with the verification "
                          "process. Once you do, re-react to the check to continue.", delete_after=15)

    if user_data is None:
        await add_new_user(self.client.pool, payload.user_id, guild.id, msg.id)
    else:
        await update_user(self.client.pool, payload.user_id, "verifyguild", guild.id)
        await update_user(self.client.pool, payload.user_id, "verifyid", msg.id)
    if not verified:
        await msg.add_reaction('❌')


async def dm_verify_react_handler(self, payload, user_data, user):
    if user_data[usr_cols.status] != "denied":
        if user_data[usr_cols.status] != "cancelled":
            if str(payload.emoji) == '✅':
                status = user_data[usr_cols.status]
                if status == 'stp_2':
                    await self.step_2_verify(payload.user_id)
                    return
                elif status == 'stp_3':
                    await self.step_3_verify(payload.user_id, reverify=False)
                    return
            elif str(payload.emoji) == '❌':
                embed = embeds.verification_cancelled()
                message = await user.fetch_message(user_data[usr_cols.verifyid])
                await message.edit(embed=embed)
                guild_db = await get_guild(self.client.pool, user_data[usr_cols.verifyguild])
                vfy_log_channel_id = guild_db[gld_cols.verifylogchannel]
                channel = await self.client.get_channel(vfy_log_channel_id)
                await channel.send(f"{user.mention} has cancelled the verification process.")
                await update_user(self.client.pool, payload.user_id, "verifyguild", None)
                await update_user(self.client.pool, payload.user_id, "verifyid", "")
                await update_user(self.client.pool, payload.user_id, "status", "cancelled")
            elif str(payload.emoji) == '👍':
                await self.step_3_verify(payload.user_id,
                                         reverify=True)
        # if str(payload.emoji) == '👍':
        #     await step_1_verify(self.client.pool, payload.user_id, user_data[usr_cols.ign])
    else:
        if str(payload.emoji) == '✅' or str(payload.emoji) == '👍':
            guild_data = await get_guild(self.client.pool, user_data[usr_cols.verifyguild])
            guild = self.client.get_guild(guild_data[gld_cols.id])
            channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
            key = user_data[usr_cols.verifykey]
            if not key:
                key = "`N/A: Re-verification`"

            fame_req = guild_data[gld_cols.nfame]
            n_maxed_req = guild_data[gld_cols.nmaxed]
            star_req = guild_data[gld_cols.nstars]
            months_req = guild_data[gld_cols.creationmonths]
            private_loc = guild_data[gld_cols.privateloc]

            async with aiohttp.ClientSession() as cs:
                async with cs.get(f"https://darkmattr.uc.r.appspot.com/?player={user_data[usr_cols.ign]}", ssl=False) as r:
                    data = await r.json()  # returns dict

            alive_fame = 0
            n_maxed = 0
            n_stars = int(data["rank"])
            location = data["player_last_seen"]

            for char in data["characters"]:
                alive_fame += int(char["fame"])
                if int(char["stats_maxed"]) == 8:
                    n_maxed += 1

            if data["fame"] and data["fame"] != "hidden":
                alive_fame = int(data["fame"])

            time = ""
            try:
                time = data['created']
            except KeyError:
                try:
                    time = data['player_first_seen']
                except KeyError:
                    pass

            months = 0
            if time != "" and time != "hidden":
                days = 0
                if "years" in time:
                    days += int(time.split(" years")[0].split("~")[1]) * 365
                    if "days" in time:
                        days += int(time.split("and ")[1].split(" days")[0])
                    elif 'day' in time:
                        days += 1
                elif "year" in time:
                    days += int(time.split(" year")[0].split("~")[1]) * 365
                    if "days" in time:
                        days += int(time.split("and ")[1].split(" days")[0])
                    elif 'day' in time:
                        days += 1
                elif "days" in time:
                    days += int(time.split(" days")[0].split("~")[1])
                months = days / 30

            fame_passed = alive_fame >= fame_req
            maxed_passed = True  # TODO: Fix This!! n_maxed >= n_maxed_req
            stars_passed = n_stars >= star_req
            months_passed = months >= months_req
            private_passed = not private_loc or location == "hidden"

            msg = await channel.send(f"Manual verify UID: {payload.user_id}",
                                     embed=embeds.verification_manual_verify(user.mention, user_data[usr_cols.ign], key, fame_passed,
                                                                             alive_fame, fame_req, maxed_passed, n_maxed, n_maxed_req,
                                                                             stars_passed, n_stars, star_req, months_passed, round(months),
                                                                             months_req, private_passed))

            await update_user(self.client.pool, payload.user_id, "status", "deny_appeal")
            await update_user(self.client.pool, payload.user_id, "verifyid", msg.id)
            await user.send("Your application is being reviewed by staff. Please wait for their decision.")
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')
        elif str(payload.emoji) == '❌':
            embed = embeds.verification_cancelled()
            await user.send(embed=embed)
            await update_user(self.client.pool, payload.user_id, "verifyguild", "")
            await update_user(self.client.pool, payload.user_id, "verifyid", "")
            await update_user(self.client.pool, payload.user_id, "status", "cancelled")


## Subverification
async def subverify_react_handler(self, payload, num, guild_data, user, guild, subverify_msg_id):
    vfy_msg = await self.client.get_channel(payload.channel_id).fetch_message(subverify_msg_id)
    if num == 1:
        role = discord.utils.get(guild.roles, id=guild_data[gld_cols.subverify1roleid])
        category_name = guild_data[gld_cols.subverify1name]
    else:
        role = discord.utils.get(guild.roles, id=guild_data[gld_cols.subverify2roleid])
        category_name = guild_data[gld_cols.subverify2name]
    logchannel = guild.get_channel(guild_data[gld_cols.subverifylogchannel])
    member = guild.get_member(user.id)
    if str(payload.emoji) == '✅':
        await vfy_msg.remove_reaction('✅', user)
        if role in member.roles:
            await user.send("You already have the role for this category! If this is an error, contact: `@Darkmatter#7321`")
            return await logchannel.send(f"{user.mention} tried to verify for `{category_name}` but already has the role.")
        try:
            await member.add_roles(role)
            embed = discord.Embed(title="Success!",
                                  description=f"You have been given access to {category_name} in {guild.name}. To remove access, "
                                              "use the ❌ in the category verification message.",
                                  color=discord.Color.green())
            await user.send(embed=embed)
            await logchannel.send(f"{user.mention} was verified for the category: `{category_name}`")
        except discord.errors.Forbidden:
            await logchannel.send("Missing permissions for: {} in guild: {}".format(user.name, guild.name))
    else:
        await vfy_msg.remove_reaction('❌', user)
        if role not in member.roles:
            await user.send(
                "You don't yet have the role for this category! To gain access please use the ✅ emoji. If this is an error, "
                "contact: `@Darkmatter#7321`")
            return await logchannel.send(
                f"{user.mention} tried to remove their verification for `{category_name}` but doesn't have the role.")
        try:
            await member.remove_roles(role)
            embed = discord.Embed(title="Success!",
                                  description=f"Your access to {category_name} in {guild.name} has been removed. To regain access, "
                                              "use the ✅ in the category verification message.",
                                  color=discord.Color.red())
            await user.send(embed=embed)
            await logchannel.send(f"{user.mention} has removed their verification for the category: `{category_name}`")
        except discord.errors.Forbidden:
            await logchannel.send("Missing permissions for: {} in guild: {}".format(user.name, guild.name))

