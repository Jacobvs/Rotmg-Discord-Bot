import datetime
import json
import logging as logger

import aiohttp
import discord
from discord.ext import commands

import checks
import embeds
import sql
import utils
from checks import manual_verify_channel, has_manage_roles
from cogs import verification, logging
from sql import get_guild, get_user, update_user, add_new_user, gld_cols, usr_cols

logger = logger.getLogger('discord')


class Moderation(commands.Cog):
    """Commands for user/server management"""

    defaultnames = ["darq", "deyst", "drac", "drol", "eango", "eashy", "eati", "eendi", "ehoni", "gharr", "iatho", "iawa", "idrae", "iri", "issz", "itani", "laen", "lauk", "lorz",
                    "oalei", "odaru", "oeti", "orothi", "oshyu", "queq", "radph", "rayr", "ril", "rilr", "risrr", "saylt", "scheev", "sek", "serl", "seus", "tal", "tiar", "uoro",
                    "urake", "utanu", "vorck", "vorv", "yangu", "yimi", "zhiar"]

    def __init__(self, client):
        self.client = client

    @commands.command(usage='listall <role>', description="List all members with a role")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def listall(self, ctx, role: discord.Role):
        # nsections = int(len(role.members)/20)-1
        # embed = discord.Embed(title=f"Members with the role: {role.name}", color=role.color)
        # for i in range(nsections):
        #     embed.add_field(name="Members", value="".join([m.mention for m in role.members[20*i:20*(i+1)]]), inline=False)
        # await ctx.send(embed=embed)
        mstrs = []
        for m in role.members:
            if " | " in m.display_name:
                mstrs.extend(m.display_name.split(" | "))
            else:
                mstrs.append(m.display_name)
        str = f"[{', '.join([''.join([c for c in m if c.isalpha()]) for m in mstrs])}]"
        await ctx.send(str)

    @commands.command(usage="listvc", description="Return a list of people in a VC")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def listvc(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("You must be in a VC to use this command!")

        mstrs = []
        for m in ctx.author.voice.channel.members:
            if " | " in m.display_name:
                mstrs.extend(m.display_name.split(" | "))
            else:
                mstrs.append(m.display_name)
        str = '["' + '", "'.join([''.join([c for c in m if c.isalpha()]) for m in mstrs]) + '"]'
        await ctx.send(str)

    @commands.command(usage="change_prefix <prefix>", description="Change the bot's prefix for all commands.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def change_prefix(self, ctx, prefix):
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)

        prefixes[str(ctx.guild.id)] = prefix

        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        await ctx.send(f"The prefix for this server has been changed to '{prefix}'.")

    @commands.command(usage="find <nickname>", description="Find a user by the specified nickname.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def find(self, ctx, member):
        if member.strip().lower() in self.defaultnames:
            embed = discord.Embed(title="Error!", description=f"`{member}` is a default name!", color=discord.Color.red())
            return await ctx.send(embed=embed)
        else:
            member = await utils.MemberLookupConverter().convert(ctx, member)
        if member.voice is None:
            vc = '❌'
        else:
            vc = f"`{member.voice.channel.name}`"

        if member.nick and " | " in member.nick:  # Check if user has an alt account
            names = member.nick.split(" | ")
            names = ["".join([c for c in n if c.isalpha()]) for n in names]
            desc = f"Found {member.mention} with the ign's: "
            desc += " | ".join(['[' + ''.join([n for n in name]) + '](https://www.realmeye.com/player/' + ''.join([n for n in name]) + ")" for name in names])
            desc += f"\nVoice Channel: {vc}"
            desc += f"\nRealm Names: `{'`, `'.join(names)}`"
        else:
            name = ''.join([i for i in member.display_name if i.isalpha()])
            desc = f"Found {member.mention} with the ign: [{name}](https://www.realmeye.com/player/{name})\nVoice Channel: {vc}"
            desc += f"\nRealm Name: `{name}`"

        embed = discord.Embed(description=desc, color=discord.Color.green())

        pdata = await sql.get_users_punishments(self.client.pool, member.id, ctx.guild.id)
        bdata = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id)
        pages = []
        if pdata:
            for i, r in enumerate(pdata, start=1):
                requester = ctx.guild.get_member(r[sql.punish_cols.r_uid])
                active = "✅" if r[sql.punish_cols.active] else "❌"
                starttime = f"Issued at: `{r[sql.punish_cols.starttime].strftime('%b %d %Y %H:%M:%S')}`"
                endtime = f"\nEnded at: `{r[sql.punish_cols.endtime].strftime('%b %d %Y %H:%M:%S')}`" if r[sql.punish_cols.endtime] else ""
                ptype = r[sql.punish_cols.type].capitalize()
                color = discord.Color.orange() if ptype == "Warn" else discord.Color.red() if ptype == "Suspend" else \
                    discord.Color.from_rgb(0, 0, 0)
                pembed = discord.Embed(title=f"Punishment Log #{i} - {ptype}", color=color)
                pembed.description = f"Punished member: {member.mention}\n**{ptype}** issued by {requester.mention if requester else '(Issuer left server)'}\nActive: {active}"
                pembed.add_field(name="Reason:", value=r[sql.punish_cols.reason], inline=False)
                pembed.add_field(name="Time:", value=starttime + endtime)
                pages.append(pembed)
        if bdata:
            for i, r in enumerate(bdata, start=1):
                requester = ctx.guild.get_member(r[sql.blacklist_cols.rid])
                active = "✅"
                starttime = f"Issued at: `{r[sql.blacklist_cols.issuetime].strftime('%b %d %Y %H:%M:%S')}`"
                btype = r[sql.blacklist_cols.type].capitalize()
                color = discord.Color.from_rgb(0, 0, 0)
                bembed = discord.Embed(title=f"Blacklist Log #{i} - {btype}", color=color)
                bembed.description = f"Punished member: {member.mention}\n**{btype}** blacklist issued by {requester.mention if requester else '(Issuer left server)'}\nActive:" \
                                     f" {active}"
                bembed.add_field(name="Reason:", value=r[sql.blacklist_cols.reason], inline=False)
                bembed.add_field(name="Time:", value=starttime)
                pages.append(bembed)
        if pdata or bdata:
            embed.add_field(name="Punishments:", value=f"Found `{len(pdata)}` Punishments in this user's history.\nFound `{len(bdata)}` Blacklists in this users history.\nUse the "
                                                       "reactions below to navigate through them.")
            pages.insert(0, embed)
            paginator = utils.EmbedPaginator(self.client, ctx, pages)
            await paginator.paginate()
        else:
            embed.add_field(name="Punishments:", value="No punishment or blacklist logs found!")
            await ctx.send(embed=embed)

    @commands.command(usage='changename <member> <newname>', description="Change the users name.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def changename(self, ctx, member: utils.MemberLookupConverter, newname):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f'https://darkmattr.uc.r.appspot.com/?player={newname}', ssl=False) as r:
                if r.status == 403:
                    print("ERROR: API ACCESS FORBIDDEN")
                    await ctx.send(f"<@{self.client.owner_id}> ERROR: API ACCESS REVOKED!.")
                data = await r.json()  # returns dict
        if not data:
            return await ctx.send("There was an issue retrieving realmeye data. Please try the command later.")

        cleaned_name = newname if 'error' in data else str(data["player"])

        res = await sql.change_username(self.client.pool, member.id, cleaned_name)
        if not res:
            embed = discord.Embed(title="Error!", description="Something went wrong, username couldn't be changed in SQL", color=discord.Color.red())
            return await ctx.send(embed=embed)

        embed = None
        for g in self.client.guilds:
            m = g.get_member(member.id)
            if m:
                name = m.display_name

                if cleaned_name.lower() in name.lower():
                    embed = discord.Embed(title="Error!", description="Name specified is the same name as the user's name currently!",
                                          color=discord.Color.red())

                separator = " | "
                s_name = name.split(separator)
                symbols = "".join([c for c in s_name[0] if not c.isalpha()])
                s_name[0] = symbols + newname
                s_name = separator.join(s_name)

                try:
                    await m.edit(nick=s_name)
                except discord.Forbidden:
                    embed = discord.Embed(title="Error!", description=f"There was an error changing this person's name in {g.name} (Perms).\n"
                                                                      f"Please message someone from that guild this and change their nickname to this manually: ` {s_name} `\
                                                                      {m.mention}",
                                          color=discord.Color.red())

        await logging.update_points(self.client, ctx.guild, ctx.author, 'changename')

        if embed is None:
            embed = discord.Embed(title="Success!", description=f"`{s_name}` is now the name of {member.mention}.",
                                  color=discord.Color.green())
        return await ctx.send(embed=embed)

    @commands.command(usage='addalt <member> <altname>', description="Add an alternate account to a user (limit 2).")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def addalt(self, ctx, member: utils.MemberLookupConverter, altname):
        async with aiohttp.ClientSession() as cs:
            async with cs.get(f"https://darkmattr.uc.r.appspot.com/?player={altname}", ssl=False) as r:
                if r.status == 403:
                    print("ERROR: API ACCESS FORBIDDEN")
                    await ctx.send(f"<@{self.client.owner_id}> ERROR: API ACCESS REVOKED!.")
                data = await r.json()  # returns dict
        if not data:
            return await ctx.send("There was an issue retrieving realmeye data. Please try the command later.")
        if 'error' in data:
            embed = discord.Embed(title='Error!', description=f"There were no players found on realmeye with the name `{altname}`.",
                                  color=discord.Color.red())
            return await ctx.send(embed=embed)

        cleaned_name = str(data["player"])
        res = await sql.add_alt_name(self.client.pool, member.id, cleaned_name, primary_name=member.display_name)
        if not res:
            embed = discord.Embed(title="Error!", description="The user specified already has 2 alts added!", color=discord.Color.red())
            return await ctx.send(embed=embed)

        name = member.display_name

        await logging.update_points(self.client, ctx.guild, ctx.author, 'addalt')

        if cleaned_name.lower() in name.lower():
            if res:
                embed = discord.Embed(title="Success!", description=f"The alt with the name `{cleaned_name}` was already added to "
                                                                    f"{member.mention}'s name, but was added to the database.")
            else:
                embed = discord.Embed(title="Error!", description="The user specified already has this alt linked to their name!",
                                      color=discord.Color.red())
            return await ctx.send(embed=embed)

        name += f" | {cleaned_name}"
        try:
            await member.edit(nick=name)
        except discord.Forbidden:
            return await ctx.send("There was an error adding the alt to this person's name (Perms).\n"
                                  f"Please copy this and add it to their name manually: ` | {cleaned_name}`\n{member.mention}")

        embed = discord.Embed(title="Success!", description=f"`{cleaned_name}` was added as an alt to {member.mention}.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='removealt <member> <altname>', description="Remove an alt from a player.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def removealt(self, ctx, member: utils.MemberLookupConverter, altname):
        res = await sql.remove_alt_name(self.client.pool, member.id, altname)

        if not res:
            embed = discord.Embed(title="Error!", description=f"The user specified doesn't have an alt in the database called `{altname}`!",
                                  color=discord.Color.red())
            await ctx.send(embed=embed)

        clean_names = []
        if altname.lower() in member.display_name.lower():
            names = member.display_name.split(" | ")
            for n in names:
                if n.lower() != altname.lower():
                    clean_names.append(n)
        nname = " | ".join(clean_names)

        try:
            await member.edit(nick=nname)
        except discord.Forbidden:
            return await ctx.send("There was an error adding the alt to this person's name (Perms).\n"
                                  f"Please copy this and replace their nickname manually: ` | {nname}`\n{member.mention}")

        embed = discord.Embed(title="Success!", description=f"`{altname}` was removed as an alt to {member.mention}.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="purge <num> [filter_type: all / contains / from] [filter: 'word' / 'sentence or words' / @member]",
                      description="Removes [num] messages from the channel\nTo delete all messages do: `purge <num> all`\nTo delete messages containing words or a sentence do: "
                                  "`purge <num> contains 'word'` or `purge <num> contains 'sentence to search'`\nTo purge messages from a member do: `purge <num> from @member`")
    @commands.guild_only()
    @commands.check_any(commands.has_permissions(manage_messages=True), checks.is_bot_owner())
    async def purge(self, ctx, num=5, type=None, filter=None):
        num += 1
        if not isinstance(num, int):
            await ctx.send("Please pass in a number of messages to delete.")
            return

        no_older_than = datetime.datetime.utcnow() - datetime.timedelta(days=14) + datetime.timedelta(seconds=1)
        if type:
            type = type.lower()
            if type == 'all':
                def check(msg):
                    return True
            elif type == 'contains':
                def check(msg):
                    return str(filter).lower() in msg.content.lower()
            elif type == 'from':
                try:
                    converter = utils.MemberLookupConverter()
                    mem = await converter.convert(ctx, filter)
                except discord.ext.commands.BadArgument as e:
                    return ctx.send(f"No members found with the name: {filter}")

                def check(msg):
                    return msg.author == mem
            else:
                return await ctx.send(f'`{type}` is not a valid filter type! Please choose from "all", "contains", "from"')
        else:
            def check(msg):
                return not msg.pinned

        messages = await ctx.channel.purge(limit=num, check=check, after=no_older_than, bulk=True)
        # if len(messages) < num:
        #     return await ctx.send("You are trying to delete messages that are older than 15 days. Discord API doesn't "
        #                           "allow bots to do this!\nYou can use the nuke command to completely clean a "
        #                           "channel.", delete_after=10)
        await ctx.send(f"Deleted {len(messages) - 1} messages.", delete_after=5)

    @commands.command(usage='nuke', description="Deletes all the messages in a channel.")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def nuke(self, ctx, confirmation=""):
        if confirmation == "I confirm this action.":
            newc = await ctx.channel.clone()
            await newc.edit(position=ctx.channel.position)
            await ctx.channel.delete()
        else:
            return await ctx.send('Please confirm you would like to do this by running: `!nuke "I confirm this '
                                  'action."`\n**__THIS WILL DELETE ALL MESSAGES IN THE CHANNEL!__**')

    @commands.command(usage="manual_verify <member> <ign>",
                      description="Manually verify someone - INCLUDE THEIR IGN HOW IT'S SPELLED IN-GAME (Including Capitalization).")
    @commands.guild_only()
    @commands.check_any(manual_verify_channel(), has_manage_roles())
    async def manual_verify(self, ctx, member: utils.MemberLookupConverter, ign):
        await ctx.message.delete()
        await logging.update_points(self.client, ctx.guild, ctx.author, 'veri')
        return await manual_verify_ext(self.client.pool, ctx.guild, member.id, ctx.author, ign)

    @commands.command(usage="manual_verify_deny <member>", description="Deny someone from manual_verification.")
    @commands.guild_only()
    @commands.check_any(manual_verify_channel(), has_manage_roles())
    async def manual_verify_deny(self, ctx, member: utils.MemberLookupConverter):
        await ctx.message.delete()
        return await manual_verify_deny_ext(self.client.pool, ctx.guild, member.id, ctx.author)

    # @commands.command(usage='pban <user> <reason>')
    # @commands.is_owner()
    # async def pban(self, ctx, user: discord.User, *, reason):
    #     # embed = discord.Embed(title="Ban Notice", description=f"You have been permanently banned from all servers this bot is in for the reason:\n{reason}",
    #     #                       color=discord.Color.red())
    #     # try:
    #     #     await user.send(embed=embed)
    #     # except discord.Forbidden:
    #     #     pass
    #
    #     for server in self.client.guilds:
    #         try:
    #             await server.ban(user)
    #             await ctx.send(f"Successfully banned from {server.name}")
    #         except discord.Forbidden:
    #             await ctx.send(f"Failed to ban in {server.name}")
    #     await ctx.send("Done.")



def setup(client):
    client.add_cog(Moderation(client))


async def manual_verify_ext(pool, guild, uid, requester, ign=None):
    """Manually verifies user with specified uid"""
    guild_data = await get_guild(pool, guild.id)
    channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
    member = guild.get_member(int(uid))
    user_data = await get_user(pool, int(uid))

    if user_data is not None:  # check if user exists in DB
        name = user_data[usr_cols.ign]
        status = user_data[usr_cols.status]
        if status != 'verified':
            if status != "stp_1" and status != "stp_2":
                if status == 'deny_appeal':
                    channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
                    try:
                        message = await channel.fetch_message(user_data[usr_cols.verifyid])
                        await message.delete()
                    except discord.NotFound:
                        pass
                if ign is not None:
                    name = ign
            elif ign is not None:
                name = ign
            else:
                await channel.send("Please specify an IGN for this user.")
                return
        else:
            await channel.send("The specified member has already been verified.")
    elif ign is not None:
        await add_new_user(pool, int(uid), guild.id, None)
        user_data = await get_user(pool, int(uid))
        name = ign
    else:
        return await channel.send("Please specify an IGN for this user.")

    await verification.complete_verification(pool, guild, guild_data, member, name, user_data, False)
    embed = discord.Embed(
        description=f"✅ {member.mention} ***has been manually verified by*** {requester.mention}***.***",
        color=discord.Color.green())
    await channel.send(embed=embed)

async def vet_manual_verify_ext(client, guild, uid, requester, msg_id):
    """Manually vet verifies user with specified uid"""
    guild_data = client.guild_db[guild.id]
    channel = guild_data[gld_cols.manualverifychannel]
    member: discord.Member = guild.get_member(int(uid))
    role = guild_data[sql.gld_cols.vetroleid]
    try:
        await member.add_roles(role)
    except discord.Forbidden:
        pass

    message = await channel.fetch_message(msg_id)
    try:
        await message.delete()
    except discord.Forbidden or discord.HTTPException or discord.NotFound:
        pass

    embed = discord.Embed(
        description=f"✅ {member.mention} ***has been manually __veteran__ verified by*** {requester.mention}***.***",
        color=discord.Color.green())
    await channel.send(embed=embed)

    await member.send(member.mention, embed=embeds.vet_verification_success(guild.name, member.mention))
    await guild_data[gld_cols.verifylogchannel].send(f"{member.mention} has been veteran verified by {requester.mention}", allowed_mentions=discord.AllowedMentions(
        everyone=False, users=False, roles=False))

async def vet_manual_verify_deny_ext(client, guild, uid, requester, msg_id):
    """Denies user from vet verifying user with specified uid"""
    guild_data = client.guild_db[guild.id]
    channel = guild_data[gld_cols.manualverifychannel]
    member: discord.Member = guild.get_member(int(uid))

    message = await channel.fetch_message(msg_id)
    try:
        await message.delete()
    except discord.Forbidden or discord.HTTPException or discord.NotFound:
        pass

    embed = embeds.vet_verification_denied(member.mention, requester.mention)
    await member.send(embed=embed)

    embed = discord.Embed(
        description=f"❌ {member.mention} ***has been denied __veteran__ verification by*** {requester.mention}***.***",
        color=discord.Color.red())
    await channel.send(embed=embed)
    await guild_data[gld_cols.verifylogchannel].send(f"{member.mention} has been denied veteran verification by {requester.mention}", allowed_mentions=discord.AllowedMentions(
        everyone=False, users=False, roles=False))


async def manual_verify_deny_ext(pool, guild, uid, requester):
    """Manually verifies user with specified uid"""
    guild_data = await get_guild(pool, guild.id)
    channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
    member = guild.get_member(int(uid))
    user_data = await get_user(pool, int(uid))

    if user_data is not None:
        status = user_data[usr_cols.status]
        if status != 'verified':
            if status == 'deny_appeal':
                channel = guild.get_channel(guild_data[gld_cols.manualverifychannel])
                message = await channel.fetch_message(user_data[usr_cols.verifyid])
                await message.delete()
        else:
            await channel.send("The specified member has already been verified.")

    await update_user(pool, member.id, "status", "appeal_denied")
    guilds = user_data[usr_cols.verifiedguilds]
    if guilds is None:
        guilds = []
    else:
        guilds = guilds.split(",")
    guilds.append(guild.name)
    # await update_user(pool, member.id, "verifiedguilds", ','.join(guilds))
    await update_user(pool, member.id, "verifyguild", None)
    await update_user(pool, member.id, "verifykey", None)
    await update_user(pool, member.id, "verifyid", None)
    embed = embeds.verification_denied(member.mention, requester.mention)
    await member.send(embed=embed)

    embed = discord.Embed(
        description=f"❌ {member.mention} ***has been denied verification by*** {requester.mention}***.***",
        color=discord.Color.red())
    await channel.send(embed=embed)


def is_not_pinned(msg):
    return False if msg.pinned else True
