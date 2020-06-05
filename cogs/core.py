import json
from datetime import datetime, timedelta

import discord
from discord.ext import commands

import sql
from checks import is_role_or_higher
from cogs import verification, raiding, moderation
from cogs.verification import guild_verify_react_handler, dm_verify_react_handler, Verification, subverify_react_handler
from sql import get_guild, get_user, add_new_guild, usr_cols, gld_cols

states = {}
rcstates = {}


class Core(commands.Cog):
    """Houses core commands & listeners for the bot"""


    def __init__(self, client):
        self.client = client
        self.start_time = datetime.now()


    @commands.command(usage="!uptime")
    @commands.has_permissions(administrator=True)
    async def uptime(self, ctx):
        """Tells how long the bot has been running."""
        uptime_seconds = round((datetime.now() - self.start_time).total_seconds())
        await ctx.send(f"Current Uptime: {'{:0>8}'.format(str(timedelta(seconds=uptime_seconds)))}")


    @commands.command(usage="!rolecount <role>")
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
                # TODO: implement proper checks
                if message.author.id not in self.client.variables.get('allowed_user_ids'):
                    await message.author.send('You do not have the permissions to use this command.')
                return

            user_data = await get_user(self.client.pool, message.author.id)

            if user_data is not None:  # TODO: implement modmail
                if user_data[usr_cols.status] == 'verified' or (
                        user_data[usr_cols.status] == 'cancelled' and user_data[usr_cols.verifiedguilds] is not None):
                    msg = "What server would you like to send this modmail to?"
                    await message.author.send(msg)
                    return
                elif user_data[usr_cols.status] == 'stp_1':
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
                    else:
                        await message.author.send("You are already verifying, react to the check to continue.", delete_after=10)
            else:
                await message.author.send("You are not verified in any guilds this bot is in yet. Please verify "
                                          "before attempting to send modmail.")


    @commands.command(usage="!help")
    async def help(self, ctx, *cog):
        """Gets all cogs and commands"""
        if not cog:
            halp = discord.Embed(title='Cogs and Uncatergorized Commands', description='Use `!help *cog*` to find out more about them!')
            cogs_desc = ''
            for x in sorted(self.client.cogs):
                if x != "CommandErrorHandler":
                    cogs_desc += f'{x}\n'
            halp.add_field(name='Cogs', value=cogs_desc[0:len(cogs_desc) - 1], inline=False)
            cmds_desc = ''
            for y in self.client.walk_commands():
                if not y.cog_name and not y.hidden:
                    cmds_desc += ('{} - {}'.format(y.usage, y.help) + '\n')
            halp.add_field(name='Developer Commands', value=cmds_desc[0:len(cmds_desc) - 1], inline=False)
            await ctx.send('', embed=halp)
        else:
            if len(cog) > 1:
                halp = discord.Embed(title='Error!', description="That's too many cogs!", color=discord.Color.red())
                await ctx.message.author.send('', embed=halp)
            else:
                found = False
                for x in self.client.cogs:
                    for y in cog:
                        if x == y.capitalize():
                            halp = discord.Embed(title=cog[0].capitalize() + ' Commands',
                                                 description=self.client.cogs[y.capitalize()].__doc__)
                            for c in self.client.get_cog(y.capitalize()).get_commands():
                                if not c.hidden:
                                    halp.add_field(name=c.usage, value=c.help, inline=False)
                            found = True
                if not found:
                    halp = discord.Embed(title='Error!', description='Unknown Cog: "' + cog[0].capitalize() + '"',
                                         color=discord.Color.red())

                await ctx.send(embed=halp)


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

            if payload.message_id == verify_message_id and str(payload.emoji) == '✅':  # handles verification reacts
                return await guild_verify_react_handler(Verification(self.client), payload, user_data, guild_data, user, guild,
                                                        verify_message_id)
            elif payload.message_id == subverify_1_msg_id and (
                    str(payload.emoji) == '✅' or str(payload.emoji) == '❌'):  # handles subverification 1
                return await subverify_react_handler(Verification(self.client), payload, 1, guild_data, user, guild, subverify_1_msg_id)
            elif payload.message_id == subverify_2_msg_id and (
                    str(payload.emoji) == '✅' or str(payload.emoji) == '❌'):  # handles subverification 2
                return await subverify_react_handler(Verification(self.client), payload, 2, guild_data, user, guild, subverify_2_msg_id)
            elif payload.channel_id in [guild_data[gld_cols.raidhc1], guild_data[gld_cols.raidhc2], guild_data[gld_cols.raidhc3],
                                        guild_data[gld_cols.vethc1]]:  # handles raiding emoji reactions
                if str(payload.emoji) == '❌' and await is_role_or_higher(guild.get_member(user.id),
                                                                         self.client.guild_db.get(guild.id)[sql.gld_cols.rlroleid]):
                    #from cogs.raiding import end_afk_check
                    return await raiding.end_afk_check(self.client.pool, guild.get_member(user.id), guild, False)
                #from cogs.raiding import afk_check_reaction_handler
                return await raiding.afk_check_reaction_handler(self.client.pool, payload, guild.get_member(user.id), guild)
            elif payload.channel_id == guild_data[gld_cols.manualverifychannel]:  # handles manual verificaions
                if str(payload.emoji) == '✅':
                    channel = guild.get_channel(payload.channel_id)
                    msg = await channel.fetch_message(payload.message_id)
                    uid = msg.content.split(": ")[1]
                    return await moderation.manual_verify_ext(self.client.pool, guild, uid, user)
                elif str(payload.emoji) == '❌':
                    channel = guild.get_channel(payload.channel_id)
                    msg = await channel.fetch_message(payload.message_id)
                    uid = int(msg.content.split(": ")[1])
                    return await moderation.manual_verify_deny_ext(self.client.pool, guild, uid, user)

        elif str(payload.emoji) in ['✅', '👍', '❌']:  # handles verification DM reactions
            if user_data is not None:
                if payload.message_id == user_data[usr_cols.verifyid]:
                    return await dm_verify_react_handler(Verification(self.client), payload, user_data, user)
        # elif str(payload.emoji) in ['✉️','🚫']: # handles modmail (FUTURE)
        elif payload.emoji.id in raiding.key_ids:  # handles AFK check key reactions
            return await raiding.confirmed_raiding_reacts(payload, user)


def setup(client):
    client.add_cog(Core(client))