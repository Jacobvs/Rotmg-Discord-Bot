import asyncio
import json
from datetime import datetime, timedelta
from os import listdir
from os.path import join, isfile

import aiohttp
import discord
import psutil
from discord.ext import commands

import sql
import utils
from cogs import verification, moderation
from cogs.verification import guild_verify_react_handler, dm_verify_react_handler, Verification, subverify_react_handler
from sql import get_guild, get_user, add_new_guild, usr_cols, gld_cols
from utils import EmbedPaginator

states = {}
rcstates = {}


class Core(commands.Cog):
    """Houses core commands & listeners for the bot"""

    def __init__(self, client):
        self.client = client
        self.start_time = datetime.now()


    @commands.command(usage="uptime", description="Tells how long the bot has been running.")
    async def uptime(self, ctx):
        uptime_seconds = round((datetime.now() - self.start_time).total_seconds())
        await ctx.send(f"Current Uptime: {'{:0>8}'.format(str(timedelta(seconds=uptime_seconds)))}")


    @commands.command(usage="report", description="Report a bug or suggest a new feature here!", aliases=['bug','feature','suggest'])
    async def report(self, ctx):
        embed = discord.Embed(title="Is this a feature or a bug?", description="Select 💎 if it's a feature, 🦟 if it's a bug.", color=discord.Color.gold())
        msg = await ctx.send(embed=embed)
        await msg.add_reaction("💎")
        await msg.add_reaction("🦟")

        def check(react, usr):
            return usr.id == ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["💎", "🦟"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                  color=discord.Color.red())
            await msg.delete()
            return await ctx.send(embed=embed)

        if str(reaction.emoji) == '💎':
           label = 'Feature'
        else:
           label = 'Bug'

        if label == 'Feature':
            desc = "```**Is your feature request related to a problem? Please describe.**\nA clear and concise description of what the problem is. " \
                   "Ex. I'm always frustrated when [...]\n\n**How would the feature work? Describe**\nAdd a description about how the feature would work " \
                   "(e.g. commands, interactions, etc)\n\n**Describe the ideal implementation.**\nA clear and concise description of what you want to happen.\n\n" \
                   "**Describe alternatives you've considered**\nA clear and concise description of any alternative solutions or features you've considered.\n\n" \
                   "**Additional context**\nAdd any other context or a screenshot about the feature request here.\n```"
        else:
            desc = "```**Describe the bug**\nA clear and concise description of what the bug is.\n\n**To Reproduce**\nSteps to reproduce the behavior:\n1. (list all steps)\n" \
                   "**Expected behavior**\nA clear and concise description of what you expected to happen.\n\n**Screenshot**\nIf applicable, add a screenshot/image to help " \
                   "explain your problem.\n\n**What server & channel did this occur in?**\nServer:\nChannel:\n```"
        embed = discord.Embed(title="Please copy the template & fill it out", description=desc, color= discord.Color.gold())
        await msg.clear_reactions()
        await msg.edit(embed=embed)

        while True:
            imageb = None
            def member_check(m):
                return m.author.id == ctx.author.id and m.channel == msg.channel
            try:
               issuemsg = await self.client.wait_for('message', timeout=1800, check=member_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't write your report in time!", color=discord.Color.red())
                await msg.edit(embed=embed)

            content = str(issuemsg.content)
            if not content:
                content = "No issue content provided."
            if issuemsg.attachments:
                imageb = issuemsg.attachments[0] if issuemsg.attachments[0].height else None
                if not imageb:
                    await ctx.send("Please only send images as attachments.", delete_after=7)
                    continue
                else:
                    imageb = await imageb.read()
                    await issuemsg.delete()
                    break
            else:
                await issuemsg.delete()
                break

        if imageb:
            img_data = await utils.image_upload(imageb, ctx, is_rc=False)
            if not img_data:
                return await ctx.send(
                    "There was an issue communicating with the image server, try again and if the issue persists – contact the developer.",
                    delete_after=10)

            image = img_data["secure_url"]
            content += f"\n\nUploaded Image:\n{image}"

        title = '[FEATURE] ' if label == 'Feature' else '[BUG] '
        title += f'Submitted by {ctx.author.display_name}'

        header = {'Authorization': f'token {self.client.gh_token}'}
        payload = {
            "title": title,
            'body': content,
            'assignee': 'Jacobvs',
            'labels': [label]
        }
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
                async with cs.request("POST", "https://api.github.com/repos/Ooga-Booga-Bot/Rotmg-Discord-Bot/issues", json=payload, headers=header) as r:
                    if r.status != 201:
                        print("GH ISSUE UPLOAD ERROR:")
                        print(r)
                        print(await r.json())
                        return None
                    else:
                        res = await r.json()
        except asyncio.TimeoutError:
            return await ctx.send("There was an issue uploading the issue, please retry the command.", delete_after=10)

        embed = discord.Embed(title="Thank You!", description="I (Darkmattr) appreciate that you took the time to fill out a report/suggestion!\nI've been notified & will get to "
                                                              f"it as soon as possible.\n\nTrack the status of your issue here:\n{res['html_url']}", color=discord.Color.green())
        await msg.edit(embed=embed)


    @commands.command(usage="status", description="Retrieve the bot's status.")
    async def status(self, ctx):
        embed = discord.Embed(title="Bot Status", color=discord.Color.dark_gold())
        nverified = await sql.get_num_verified(self.client.pool)
        embed.add_field(name="Bot latency:", value=f"**`{round(self.client.latency*1000, 2)}`** Milliseconds.")
        mcount = 0
        for g in self.client.guilds:
            mcount += g.member_count
        embed.add_field(name="Connected Servers:",
                        value=f"**`{len(self.client.guilds)}`** servers with **`{mcount}`** total members.")
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Verified Raiders:", value=f"**`{nverified[0]}`** verified raiders.")
        lines = line_count('/home/pi/Rotmg-Bot/') + line_count('/home/pi/Rotmg-Bot/cogs') + line_count(
            '/home/pi/Rotmg-Bot/cogs/Raiding') + line_count('/home/pi/Rotmg-Bot/cogs/Minigames')
        embed.add_field(name="Lines of Code:", value=(f"**`{lines}`** lines of code."))
        embed.add_field(name="\u200b", value="\u200b")
        embed.add_field(name="Server Status:",
                        value=(f"```yaml\nServer: 0 GHz Potato\nCPU: {psutil.cpu_percent()}% utilization."
                               f"\nMemory: {psutil.virtual_memory().percent}% utilization."
                               f"\nDisk: {psutil.disk_usage('/').percent}% utilization."
                               f"\nNetwork: {round(psutil.net_io_counters().bytes_recv*0.000001)} MB in "
                               f"/ {round(psutil.net_io_counters().bytes_sent*0.000001)} MB out.```"), inline=False)
        embed.add_field(name="Development Progress", value="To see what I'm working on, click here:\nhttps://github.com/Ooga-Booga-Bot/Rotmg-Discord-Bot/projects/1", inline=False)
        if ctx.guild:
            appinfo = await self.client.application_info()
            embed.add_field(name=f"Bot author:", value=f"{appinfo.owner.mention} - DM me if something's broken or to request a feature!",
                            inline=False)
        else:
            embed.add_field(name=f"Bot author:", value="__Darkmatter#7321__ - DM me if something's broken or to request a feature!",
                            inline=False)
        await ctx.send(embed=embed)


    @commands.command(usage="rolecount <role>", description="Counts the number of people who have a role.")
    async def rolecount(self, ctx, role: discord.Role):
        embed = discord.Embed(color=role.color).add_field(name=f"Members in {role.name}", value=str(len(role.members)))
        await ctx.send(embed=embed)

    # Event listeners
    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        """Add prefix & entry in rotmg.guilds table on guild join"""
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)
        prefixes.update({guild.id: '!'})
        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        await add_new_guild(self.client.pool, guild.id, guild.name)


    @commands.Cog.listener()
    async def on_guild_leave(self, guild):
        """Remove guild from data"""
        with open('data/prefixes.json', 'r') as file:
            prefixes = json.load(file)
        prefixes.pop(str(guild.id))
        with open('data/prefixes.json', 'w') as file:
            json.dump(prefixes, file, indent=4)

        # TODO: Remove guilds and user-data from sql


    @commands.Cog.listener()
    async def on_message(self, message):
        # If msg is a dm to the bot (A. verification, B. Mod-mail)
        if message.guild is None and message.author != self.client.user:
            # If DM is a command
            if message.content[0] == '!':
                return

            user_data = await get_user(self.client.pool, message.author.id)

            if user_data is not None:
                # if user_data[usr_cols.status] == 'verified' or (
                #         user_data[usr_cols.status] == 'cancelled' and user_data[usr_cols.verifiedguilds] is not None):
                #     msg = "What server would you like to send this modmail to?"
                #     await message.author.send(msg)
                #     return
                if user_data[usr_cols.status] == 'stp_1':
                    if not message.content.isalpha():
                        return await message.author.send("Please provide your username only. No numbers or symbols", delete_after=10)
                    # if ign_exists(message.content.strip()): TODO: Find a way to fix this
                    #     return await message.author.send(f"This username has already been taken.
                    #                                      "If you believe this is a bug DM the developer: __Darkmatter#7321__")
                    await verification.step_1_verify(self.client.pool, message.author, message.content.strip())
                else:
                    if user_data[usr_cols.status] == 'cancelled':
                        if user_data[usr_cols.verifiedguilds] is None:
                            await verification.step_1_verify(self.client.pool, message.author, message.content.strip())
                        else:
                            await message.author.send("You are not verified in any guilds this bot is in yet. Please "
                                                      "verify before attempting to send modmail.")
                    if user_data[usr_cols.status] == 'appeal_denied':
                        await message.author.send(
                            "You have been denied from verifying in this server. Contact a moderator+ if you think this is a mistake.")
                    # elif user_data[usr_cols.status] == 'verified':
                    #     await message.author.send('You are already verified. If you are attempting to send modmail, '
                    #                               'please use the `!mm` command.')
                    elif user_data[usr_cols.status] == 'stp_2' or user_data[usr_cols.status] == 'stp_3':
                        await message.author.send("You are already verifying, react to the check to continue.", delete_after=10)
            else:
                await message.author.send("You are not verified in any guilds this bot is in yet. Please verify "
                                          "before attempting to send modmail.")


    @commands.bot_has_permissions(add_reactions=True)
    @commands.command(usage="help [command/cog]",
        aliases=["h"], description="Shows the help menu or information for a specific command or cog when specified.")
    async def help(self, ctx, *, opt: str = None):
        if opt:
            command = self.client.get_command(opt.lower())
            if not command:
                cog = self.client.get_cog(opt.capitalize())
                if not cog:
                    return await ctx.send(
                        embed=discord.Embed(description=f"That command/cog does not exist. Use `{ctx.prefix}help` to see all the commands.",
                            color=discord.Color.red(), ))
                cog_commands = cog.get_commands()
                embed = discord.Embed(title=opt.capitalize(), description=f"{cog.description}\n\n`<>` Indicates a required argument.\n"
                                                                 "`[]` Indicates an optional argument.\n", color=discord.Color.blue(), )
                embed.set_author(name=f"{self.client.user.name} Help Menu", icon_url=self.client.user.avatar_url)
                embed.set_thumbnail(url=self.client.user.avatar_url)
                embed.set_footer(
                    text=f"Use {ctx.prefix}help <command> for more information on a command.")
                for cmd in cog_commands:
                    if cmd.hidden is False:
                        name = ctx.prefix + cmd.usage
                        if len(cmd.aliases) > 1:
                            name += f" | Aliases – `{'`, `'.join([ctx.prefix + a for a in cmd.aliases])}`"
                        elif len(cmd.aliases) > 0:
                            name += f" | Alias – {ctx.prefix+cmd.aliases[0]}"
                        embed.add_field(name=name, value=cmd.description, inline=False)
                return await ctx.send(embed=embed)

            embed = discord.Embed(title=command.name, description=command.description, colour=discord.Color.blue())
            usage = "\n".join([ctx.prefix + x.strip() for x in command.usage.split("\n")])
            embed.add_field(name="Usage", value=f"```{usage}```", inline=False)
            if len(command.aliases) > 1:
                embed.add_field(name="Aliases", value=f"`{'`, `'.join(command.aliases)}`")
            elif len(command.aliases) > 0:
                embed.add_field(name="Alias", value=f"`{command.aliases[0]}`")
            return await ctx.send(embed=embed)
        all_pages = []
        page = discord.Embed(title=f"{self.client.user.name} Help Menu",
            description="Thank you for using Ooga-Booga! Please direct message `Darkmatter#7321` if you find bugs or have suggestions!",
            color=discord.Color.blue(), )
        page.set_thumbnail(url=self.client.user.avatar_url)
        page.set_footer(text="Use the reactions to flip pages.")
        all_pages.append(page)
        page = discord.Embed(title=f"{self.client.user.name} Help Menu", colour=discord.Color.blue())
        page.set_thumbnail(url=self.client.user.avatar_url)
        page.set_footer(text="Use the reactions to flip pages.")
        page.add_field(name="About Ooga-Booga",
            value="This bot was built to as a way to give back to the ROTMG community by facilitating more organized raids and allowing "
                  "server owners to create new and exciting raiding discords for the community!", inline=False, )
        page.add_field(name="Getting Started",
            value=f"For a full list of commands, see `{ctx.prefix}help`. Browse through the various commands to get comfortable with using "
                  "them, and as always if you have questions or need help – DM `Darkmatter#7321`!", inline=False, )
        all_pages.append(page)
        for _, cog_name in enumerate(sorted(self.client.cogs)):
            if cog_name in ["Owner", "Admin"]:
                continue
            cog = self.client.get_cog(cog_name)
            cog_commands = cog.get_commands()
            if len(cog_commands) == 0:
                continue
            page = discord.Embed(title=cog_name, description=f"{cog.description}\n\n`<>` Indicates a required argument.\n"
                                                             "`[]` Indicates an optional argument.\n",
                color=discord.Color.blue(), )
            page.set_author(name=f"{self.client.user.name} Help Menu", icon_url=self.client.user.avatar_url)
            page.set_thumbnail(url=self.client.user.avatar_url)
            page.set_footer(text=f"Use the reactions to flip pages | Use {ctx.prefix}help <command> for more information on a command.")
            for cmd in cog_commands:
                if cmd.hidden is False:
                    name = ctx.prefix + cmd.usage
                    if len(cmd.aliases) > 1:
                        name += f" | Aliases – `{'`, `'.join([ctx.prefix + a for a in cmd.aliases])}`"
                    elif len(cmd.aliases) > 0:
                        name += f" | Alias – `{ctx.prefix+cmd.aliases[0]}`"
                    page.add_field(name=name, value=cmd.description, inline=False)
            all_pages.append(page)
        paginator = EmbedPaginator(self.client, ctx, all_pages)
        await paginator.paginate()

    @commands.command(name='commands', usage="commands", description="View a full list of all available commands.",
                      aliases=["cmd"])
    async def commandlist(self, ctx):
        embed = discord.Embed(title="Command List", description="A full list of all available commands.\n", color=discord.Color.teal())
        for _, cog_name in enumerate(sorted(self.client.cogs)):
            if cog_name in ["Owner", "Admin"]:
                continue
            cog = self.client.get_cog(cog_name)
            cog_commands = cog.get_commands()
            if len(cog_commands) == 0:
                continue
            cmds = "```yml\n" + ", ".join([ctx.prefix + cmd.name for cmd in cog_commands]) + "```"
            embed.add_field(name=cog.qualified_name + " Commands", value=cmds, inline=False)
        await ctx.send(embed=embed)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.user_id == self.client.user.id:
            return

        user_data = await get_user(self.client.pool, payload.user_id)
        user = self.client.get_user(payload.user_id)

        # check if reaction is in dm's or in guild
        if payload.guild_id is not None:
            guild = self.client.get_guild(payload.guild_id)
            guild_data = await get_guild(self.client.pool, guild.id)
            verify_message_id = guild_data[gld_cols.verificationid]
            subverify_1_msg_id = guild_data[gld_cols.subverify1id]
            subverify_2_msg_id = guild_data[gld_cols.subverify2id]

            if payload.message_id in self.client.raid_db[guild.id]['afk']:
                afk = self.client.raid_db[guild.id]['afk'][payload.message_id]
                await afk.reaction_handler(payload)
            elif payload.message_id in self.client.raid_db[guild.id]['cp']:
                afk = self.client.raid_db[guild.id]['cp'][payload.message_id]
                await afk.cp_handler(payload)

            elif payload.message_id == verify_message_id and str(payload.emoji) == '✅':  # handles verification reacts
                blacklisted = await sql.get_blacklist(self.client.pool, user.id, payload.guild_id, 'verification')
                if blacklisted:
                    return await user.send("You have been blacklisted from verifying in this server! Contact a security+ if you believe this to be a mistake!")
                return await guild_verify_react_handler(Verification(self.client), payload, user_data, guild_data, user, guild,
                                                        verify_message_id)
            elif payload.message_id == subverify_1_msg_id and (
                    str(payload.emoji) == '✅' or str(payload.emoji) == '❌'):  # handles subverification 1
                return await subverify_react_handler(Verification(self.client), payload, 1, guild_data, user, guild, subverify_1_msg_id)
            elif payload.message_id == subverify_2_msg_id and (
                    str(payload.emoji) == '✅' or str(payload.emoji) == '❌'):  # handles subverification 2
                return await subverify_react_handler(Verification(self.client), payload, 2, guild_data, user, guild, subverify_2_msg_id)
            elif payload.channel_id == guild_data[gld_cols.manualverifychannel]:  # handles manual verificaions
                if str(payload.emoji) in ['✅', '❌']:
                    channel = guild.get_channel(payload.channel_id)
                    msg = await channel.fetch_message(payload.message_id)
                    uid = msg.content.split(": ")[1]
                    if str(payload.emoji) == '✅':
                        return await moderation.manual_verify_ext(self.client.pool, guild, uid, user)
                    else:
                        return await moderation.manual_verify_deny_ext(self.client.pool, guild, uid, user)

        elif str(payload.emoji) in ['✅', '👍', '❌']:  # handles verification DM reactions
            if user_data is not None:
                if payload.message_id == user_data[usr_cols.verifyid]:
                    return await dm_verify_react_handler(Verification(self.client), payload, user_data, user)
        # elif str(payload.emoji) in ['✉️','🚫']: # handles modmail (FUTURE)


def setup(client):
    client.add_cog(Core(client))

def line_count(path):
    """Count total lines of code in specified path"""
    file_list = [join(path, file_p) for file_p in listdir(path) if isfile(join(path, file_p))]
    total = 0
    for file_path in file_list:
        if file_path[-3:] == ".py":  # Ensure only python files are counted
            try:
                count = 0
                with open(file_path, encoding="ascii", errors="surrogateescape") as current_file:
                    for l in current_file:
                        count += 1
            except IOError:
                return -1
            if count >= 0:
                total += count
    return total
