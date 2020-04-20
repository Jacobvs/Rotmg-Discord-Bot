import json
import random
import string

import discord
import requests
from discord.ext import commands

import embeds

from sql import get_guild, get_user, update_user, ign_exists, update_guild, add_new_user, usr_cols, gld_cols


class Verification(commands.Cog):
    "Verification Commands"

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
        try:
            data = requests.get('https://localhost/?player={}'.format(user_data[usr_cols.ign]), verify=False).json()
        except requests.exceptions.HTTPError:
            print("THIS IS BAD")
            await update_user(self.client.pool, user_id, "status", "stp_1")
            embed = embeds.verification_dm_start()
            await member.send("There has been an issue with retrieving data from realmeye. Ensure your profile is public. If this problem persists contact the developer.")
            return await member.send(embed=embed)

        if not data:
            await update_user(user_id, "status", "stp_1")
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
            print(4.5)
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
            if "years" in time or "year" in time:
                if "years" in time:
                    days += int(time.split(" years")[0].split("~")[1])*365
                else:
                    days += 365
                if "days" in time:
                    days += int(time.split("and ")[1].split(" days")[0])
            elif "days" in time:
                days += int(time.split(" days")[0].split("~")[1])
            months = int(days/30)
        else:
            embed = embeds.verification_private_time()
            await member.send(embed=embed)
            return await channel.send(f"{member.mention} has hidden their account creation date.")

        fame_passed = alive_fame >= fame_req
        maxed_passed = n_maxed >= n_maxed_req
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
                    await complete_verification(self.client.pool, guild, guild_data, member, name, user_data, reverify)
                    await channel.send(f"{member.mention} has completed verification.")
                else:
                    embed = embeds.verification_bad_reqs(guild_data[gld_cols.reqsmsg], fame_passed, maxed_passed, stars_passed, months_passed, private_passed)
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


    # TODO: add support for multiple servers w/ independent reqs
    @commands.command(usage="!add_verify_msg")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_verify_msg(self, ctx):
        """Add the verification message to channel"""

        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        embed = embeds.verification_check_msg(guild_db[gld_cols.reqsmsg], guild_db[gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        await update_guild(self.client.pool, ctx.guild.id, "verificationid", message.id)

    @commands.command(usage="!add_first_subverify")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_first_subverify(self, ctx):
        """Add the verification message to channel"""

        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        embed = embeds.subverify_msg(guild_db[gld_cols.subverify1name], guild_db[gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        await update_guild(self.client.pool, ctx.guild.id, "subverify1id", message.id)

    @commands.command(usage="!add_second_subverify")
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def add_second_subverify(self, ctx):
        """Add the verification message to channel"""

        guild_db = await get_guild(self.client.pool, ctx.guild.id)
        embed = embeds.subverify_msg(guild_db[gld_cols.subverify2name], guild_db[gld_cols.supportchannelname])
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
        await message.add_reaction("❌")
        await ctx.message.delete()

        # Save verification message id for later to check reacts with
        await update_guild(self.client.pool, ctx.guild.id, "subverify2id", message.id)




def setup(client):
    client.add_cog(Verification(client))


async def step_1_verify(pool, user, ign):
    embed = embeds.verification_step_1(ign)
    msg = await user.send(embed=embed)
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")

    await update_user(pool, user.id, "ign", ign)
    await update_user(pool, user.id, "status", "stp_2")
    await update_user(pool, user.id, "verifyid", msg.id)


async def complete_verification(pool, guild, guild_data, member, name, user_data, reverify):
    role = discord.utils.get(guild.roles, id=guild_data[gld_cols.verifiedroleid])
    tag = member.name
    try:
        await member.add_roles(role)
        if tag.lower() == name.lower():
            await member.edit(nick=f"{name} .")
        else:
            await member.edit(nick=name)
    except discord.errors.Forbidden:
        print("Missing permissions for: {} in guild: {}".format(member.name, guild.name))

    embed = embeds.verification_success(guild.name, member.mention)
    await member.send(embed=embed)
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
    await vfy_msg.remove_reaction('✅', user)

    if user_data is not None:
        verified_guilds = user_data[usr_cols.verifiedguilds]
        status = user_data[usr_cols.status]
        if verified_guilds is not None:
            verified_guilds = verified_guilds.split(",")
            if guild.name in verified_guilds:
                if status == "appeal_denied":
                    return await user.send("You have been denied from verifying in this server. Contact a moderator+ if you think this is a mistake.")
                elif user_data[usr_cols.status] == "deny_appeal":
                    return await user.send(
                        "You do not meet the requirements of this server, appeal with the check above or contact a moderator+ if you think this is a mistake.")
                verified = True
                embed = embeds.verification_already_verified()
                msg = await user.send(embed=embed)
            elif status == "cancelled":
                await update_user(self.client.pool, user.id, "status", "stp_1")
                embed = embeds.verification_dm_start()
                channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
                await channel.send(f"{user.mention} is re-verifying after cancelling.")
                msg = await user.send(embed=embed)
            else:
                embed = embeds.verification_already_verified_complete(verified_guilds,
                                                                      user_data[usr_cols.ign])
                msg = await user.send(embed=embed)
                await msg.add_reaction('👍')
                await msg.add_reaction('❌')  # TODO: test cancel
                await update_user(self.client.pool, user.id, "verifyid", msg.id)
                await update_user(self.client.pool, user.id, "verifyguild", guild.id)
                channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
                await channel.send(f"{user.mention} is re-verifying for this guild.")
                return
        elif status == "denied":
            embed = embeds.verification_bad_reqs(guild_data[gld_cols.reqsmsg])
            msg = await user.send(embed=embed)
            await msg.add_reaction('✅')
            await update_user(self.client.pool, payload.user_id, "verifyid", msg.id)
        elif status == "deny_appeal":
            await user.send("Your application is being reviewed by staff. Please wait for their decision.")
        elif status != "stp_1" and status != "stp_2" and status != "stp_3":
            embed = embeds.verification_dm_start()
            channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
            await channel.send(f"{user.mention} has started the verification process.")
            msg = await user.send(embed=embed)

    else:
        embed = embeds.verification_dm_start()
        channel = self.client.get_channel(guild_data[gld_cols.verifylogchannel])
        await channel.send(f"{user.mention} has started the verification process.")
        msg = await user.send(embed=embed)

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
                channel = self.client.get_channel(await get_guild(user_data[usr_cols.verifyguild])[
                                                      gld_cols.verifylogchannel])  # unknown colum none in where clause
                await channel.send(f"{user.mention} has cancelled the verification process.")
                await update_user(self.client.pool, payload.user_id, "verifyguild", None)
                await update_user(self.client.pool, payload.user_id, "status", "cancelled")
            elif str(payload.emoji) == '👍':
                await self.step_3_verify(payload.user_id, reverify=True)
        # if str(payload.emoji) == '👍':
        #     await step_1_verify(self.client.pool, )
    else:
        if str(payload.emoji) == '✅' or str(payload.emoji) == '👍':
            guild_data = await get_guild(self.client.pool, user_data[usr_cols.verifyguild])
            guild = self.client.get_guild(guild_data[gld_cols.id])
            channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
            key = user_data[usr_cols.verifykey]
            if not key:
                key = "`N/A: Re-verification`"

            with open('data/prefixes.json', 'r') as file:
                prefixes = json.load(file)

            fame_req = guild_data[gld_cols.nfame]
            n_maxed_req = guild_data[gld_cols.nmaxed]
            star_req = guild_data[gld_cols.nstars]
            months_req = guild_data[gld_cols.creationmonths]
            req_all = guild_data[gld_cols.reqall]
            private_loc = guild_data[gld_cols.privateloc]

            data = requests.get('https://localhost/?player={}'.format(user_data[usr_cols.ign]), verify=False).json()

            alive_fame = 0
            n_maxed = 0
            name = str(data["player"])
            n_stars = int(data["rank"])
            location = data["player_last_seen"]

            for char in data["characters"]:
                alive_fame += int(char["fame"])
                if int(char["stats_maxed"]) == 8:
                    n_maxed += 1

            if data["fame"] and data["fame"] != "hidden":
                alive_fame = int(data["fame"])

            time = ""
            if "created" in data:
                time = data["created"]
            elif "player_first_seen" in data:
                time = data["player_first_seen"]

            months = 0
            if time and time != "hidden":
                days = 0
                if "years" in time:
                    days += int(time.split(" years")[0].split("~")[1]) * 365
                    if "days" in time:
                        days += int(time.split("and ")[1].split(" days")[0])
                elif "days" in time:
                    days += int(time.split(" days")[0].split("~")[1])
                months = days / 30

            fame_passed = alive_fame >= fame_req
            maxed_passed = n_maxed >= n_maxed_req
            stars_passed = n_stars >= star_req
            months_passed = months >= months_req
            private_passed = not private_loc or location == "hidden"

            msg = await channel.send(f"Manual verify UID: {payload.user_id}",
                embed=embeds.verification_manual_verify(user.mention, user_data[usr_cols.ign],
                                                        key, fame_passed, alive_fame, fame_req, maxed_passed, n_maxed, n_maxed_req, stars_passed, n_stars, star_req, months_passed, round(months), months_req, private_passed))
            await update_user(payload.user_id, "status", "deny_appeal")
            await update_user(payload.user_id, "verifyid", msg.id)
            await user.send("Your application is being reviewed by staff. Please wait for their decision.")
            await msg.add_reaction('✅')
            await msg.add_reaction('❌')
        elif str(payload.emoji) == '❌':
            embed = embeds.verification_cancelled()
            await user.send(embed=embed)
            await update_user(payload.user_id, "verifyguild", "")
            await update_user(payload.user_id, "verifyid", "")
            await update_user(payload.user_id, "status", "cancelled")

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
                description=f"You have been given access to {category_name} in {guild.name}. To remove access, use the ❌ in the category verification message.",
                color=discord.Color.green())
            await user.send(embed=embed)
            await logchannel.send(f"{user.mention} was verified for the category: `{category_name}`")
        except discord.errors.Forbidden:
            await logchannel.send("Missing permissions for: {} in guild: {}".format(user.name, guild.name))
    else:
        await vfy_msg.remove_reaction('❌', user)
        if role not in member.roles:
            await user.send("You don't yet have the role for this category! To gain access please use the ✅ emoji. If this is an error, contact: `@Darkmatter#7321`")
            return await logchannel.send(f"{user.mention} tried to remove their verification for `{category_name}` but doesn't have the role.")
        try:
            await member.remove_roles(role)
            embed = discord.Embed(
                title="Success!",
                description=f"Your access to {category_name} in {guild.name} has been removed. To regain access, use the ✅ in the category verification message.",
                color=discord.Color.red()
            )
            await user.send(embed=embed)
            await logchannel.send(f"{user.mention} has removed their verification for the category: `{category_name}`")
        except discord.errors.Forbidden:
            await logchannel.send("Missing permissions for: {} in guild: {}".format(user.name, guild.name))