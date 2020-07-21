import asyncio
import datetime

import discord
from discord.ext import commands

import checks
import sql
import utils


class Punishments(commands.Cog):
    """Various commands to punish members

    For duration use this format: D for days, H for hours, M for minutes, S for seconds.
        Examples: 2D, "1D 2H", 30M, etc. """
    def __init__(self, client):
        self.client = client


    # @commands.command(usage="plogs [member]", description="View/Edit punishment logs for the entire server or specify a person to "
    #                                                       "view/edit logs for.")
    # @commands.guild_only()
    # @commands.has_permissions(administrator=True)
    # async def plogs(self, ctx, member: utils.MemberLookupConverter = None):


    @commands.command(usage="warn <member> <reason>", description="Warn a member for breaking the rules.")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def warn(self, ctx, member: utils.MemberLookupConverter, *, reason):
        await sql.add_punishment(self.client.pool, member.id, ctx.guild.id, 'warn', ctx.author.id, None, reason)
        await self.send_log(ctx.guild, member, ctx.author, 'warn', None, reason)
        embed = discord.Embed(title="Success!", description=f"`{member.display_name}` was successfully warned for reason:\n{reason}.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="mute <member> <duration> <reason>",
                      description="Prevent the member from sending messages or adding reactions.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def mute(self, ctx, member: utils.MemberLookupConverter, duration: utils.Duration, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot mute `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot mute `{member.display_name}` due to roles.')
        if ctx.author.top_role <= member.top_role:
            return await ctx.send(f'Cannot mute `{member.display_name}` as you have equal or lower roles than them.')
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.send(f'Cannot suspend `{member.display_name}` as the bot has equal or lower roles than them.')
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'mute')
        if already_active:
            return await ctx.send(f"{member.mention} already has an active mute!")
        await sql.add_punishment(self.client.pool, member.id, ctx.guild.id, 'mute', ctx.author.id, duration, reason)
        await self.send_log(ctx.guild, member, ctx.author, 'mute', duration, reason)

        tsecs = (duration - datetime.datetime.utcnow()).total_seconds()
        overwrite = discord.PermissionOverwrite(add_reactions=False, send_messages=False)
        for channel in ctx.guild.text_channels:
            permissions = channel.permissions_for(member)
            if permissions.read_messages:
                await channel.set_permissions(member, overwrite=overwrite, reason=reason)

        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully muted for reason:\n{reason}.\nDuration: "
                                          f"{duration_formatter(tsecs, 'Mute')}",
                              color=discord.Color.green())
        await ctx.send(embed=embed)
        t = self.client.loop.create_task(punishment_handler(self.client, ctx.guild, member, 'mute', tsecs))
        self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'mute'] = t

    @commands.command(usage='unmute <member> <reason>', description="Un-mute the specified member.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unmute(self, ctx, member: utils.MemberLookupConverter, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'mute')
        if not already_active:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` as they have no active mutes!')
        if self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'mute']:
            task = self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'mute']
            task.cancel()
        await unmute(self.client.pool, ctx.guild, member)
        await send_update_embeds(self.client, ctx.guild, member, True, False, ctx.author, reason)
        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully unmuted.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='suspend <member> <duration> <reason>',
                      description="Suspend a member, assigning them the suspended role & removing all other roles while suspended.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def suspend(self, ctx, member: utils.MemberLookupConverter, duration: utils.Duration, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot suspend `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot suspend `{member.display_name}` due to roles.')
        if ctx.author.top_role <= member.top_role:
            return await ctx.send(f'Cannot suspend `{member.display_name}` as you have equal or lower roles than them.')
        if ctx.guild.me.top_role <= member.top_role:
            return await ctx.send(f'Cannot suspend `{member.display_name}` as the bot has equal or lower roles than them.')
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'suspend')
        if already_active:
            return await ctx.send(f"{member.mention} already has an active suspension!")

        tsecs = (duration - datetime.datetime.utcnow()).total_seconds()
        suspendrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.suspendedrole]
        verifiedrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.verifiedroleid]
        roleids = {}
        for i, r in enumerate(member.roles[1:]):
            if r != verifiedrole and not r.managed:
                roleids[i] = r.id

        await sql.add_punishment(self.client.pool, member.id, ctx.guild.id, 'suspend', ctx.author.id, duration, reason, roleids)
        await self.send_log(ctx.guild, member, ctx.author, 'suspend', duration, reason)

        roles = []
        for r in member.roles[1:]:
            if not r.managed:
                roles.append(r)
                await member.remove_roles(r)

        await member.add_roles(suspendrole)

        if member.voice:
            await member.move_to(None, reason="Suspension")

        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully suspended for reason:\n{reason}.\nDuration: "
                                          f"{duration_formatter(tsecs, 'Suspended')}", color=discord.Color.green())
        await ctx.send(embed=embed)
        t = self.client.loop.create_task(punishment_handler(self.client, ctx.guild, member, 'suspend', tsecs, roles))
        self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'suspend'] = t


    @commands.command(usage="unsuspend <member> <reason>", description="Un-suspend the specified member.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unsuspend(self, ctx, member: utils.MemberLookupConverter, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'suspend')
        if not already_active:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` as they have no active suspensions!')

        if self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'suspend']:
            task = self.client.active_punishments[str(ctx.guild.id)+str(member.id)+'suspend']
            task.cancel()
        suspendrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.suspendedrole]
        verifiedrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.verifiedroleid]
        roles = await sql.get_suspended_roles(self.client.pool, member.id, ctx.guild)
        await unsuspend(self.client.pool, ctx.guild, suspendrole, verifiedrole, member, roles)
        await send_update_embeds(self.client, ctx.guild, member, False, False, ctx.author, reason)
        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully un-suspended.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='vblacklist <member> <reason>', description="Blacklist a user from verifying in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def vblacklist(self, ctx, member: utils.MemberLookupConverter, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot vblacklist `{member.display_name}` (is a bot).')
        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot vblacklist `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'verification')
        if exists:
            return await ctx.send(f"That member ({member.mention}) already has an active verification blacklist!")
        await sql.add_blacklist(self.client.pool, member.id, ctx.guild.id, ctx.author.id, 'verification', reason)
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully blacklisted from verification!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)

    @commands.command(usage='mblacklist <member> <reason>', description="Blacklist a user from sending modmail in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def mblacklist(self, ctx, member: utils.MemberLookupConverter, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot mblacklist `{member.display_name}` (is a bot).')

        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot mblacklist `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'modmail')
        if exists:
            return await ctx.send(f"That member ({member.mention}) already has an active modmail blacklist!")
        await sql.add_blacklist(self.client.pool, member.id, ctx.guild.id, ctx.author.id, 'modmail', reason)
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully blacklisted from sending modmail!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)


    @commands.command(usage='rblacklist <member> <reason>', description="Blacklist a user from reporting a bug in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def rblacklist(self, ctx, member: utils.MemberLookupConverter, *, reason):
        if member.bot:
            return await ctx.send(f'Cannot rblacklist `{member.display_name}` (is a bot).')

        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot rblacklist `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'reporting')
        if exists:
            return await ctx.send(f"That member ({member.mention}) already has an active reporting blacklist!")
        await sql.add_blacklist(self.client.pool, member.id, ctx.guild.id, ctx.author.id, 'reporting', reason)
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully blacklisted from reporting!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)


    @commands.command(usage='unvblacklist <member>', description="Un-Blacklist a user from verifying in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unvblacklist(self, ctx, member: utils.MemberLookupConverter):
        if member.bot:
            return await ctx.send(f'Cannot un-vblacklist `{member.display_name}` (is a bot).')

        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot un-vblacklist `{member.display_name}` due to roles.')
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'verification')
        if not exists:
            return await ctx.send(f"That member ({member.mention}) doesn't have an active verification blacklist!")
        await sql.remove_blacklist(self.client.pool, member.id, ctx.guild.id, 'verification')
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully un-blacklisted from verification!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)

    @commands.command(usage='unmblacklist <member>', description="Un-Blacklist a user from sending modmail in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unmblacklist(self, ctx, member: utils.MemberLookupConverter):
        if member.bot:
            return await ctx.send(f'Cannot un-mblacklist `{member.display_name}` (is a bot).')

        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot un-mblacklist `{member.display_name}` due to roles.')
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'modmail')
        if not exists:
            return await ctx.send(f"That member ({member.mention}) doesn't have an active modmail blacklist!")
        await sql.remove_blacklist(self.client.pool, member.id, ctx.guild.id, 'modmail')
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully un-blacklisted from modmail!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)

    @commands.command(usage='unrblacklist <member>', description="Un-Blacklist a user from reporting a bug in this server.")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unrblacklist(self, ctx, member: utils.MemberLookupConverter):
        if member.bot:
            return await ctx.send(f'Cannot un-rblacklist `{member.display_name}` (is a bot).')

        if ctx.author.id not in self.client.owner_ids:
            if member.guild_permissions.kick_members:
                return await ctx.send(f'Cannot un-rblacklist `{member.display_name}` due to roles.')
        exists = await sql.get_blacklist(self.client.pool, member.id, ctx.guild.id, 'reporting')
        if not exists:
            return await ctx.send(f"That member ({member.mention}) doesn't have an active reporting blacklist!")
        await sql.remove_blacklist(self.client.pool, member.id, ctx.guild.id, 'reporting')
        embed = discord.Embed(title="Success!", description=f"{member.mention} was successfully un-blacklisted from reporting!", color=discord.Color.green())
        embed.add_field(name="Requester:", value=ctx.author.mention)
        await ctx.send(embed=embed)


    #TODO: Add change duration command
    #TODO: add proof optional to punishment

    async def send_log(self, guild, user, requester, ptype, duration, reason):
        channel = self.client.guild_db.get(guild.id)[sql.gld_cols.punishlogchannel]
        color = discord.Color.lighter_grey() if ptype == 'mute' else discord.Color.orange() if ptype == 'warn' else discord.Color.red() \
            if ptype == 'suspend' else discord.Color.from_rgb(0, 0, 0)
        if duration:
            tsecs = (duration - datetime.datetime.utcnow()).total_seconds()
        if ptype == 'warn' or ptype == 'blacklist':
            fduration = ''
        else:
            fduration = duration_formatter(tsecs, ptype)

        ptype = "Mute" if ptype == 'mute' else "Warning" if ptype == 'warn' else "Suspension" if ptype == 'suspend' else "Blacklist"

        embed = discord.Embed(title=f'{ptype} Info', description=fduration+"\n", color=color)
        embed.add_field(name=f'User Punished: {user.display_name}', value=f"{user.mention}\nJoined at: {user.joined_at}")
        embed.add_field(name=f'Requester: {requester.display_name}', value=f"{requester.mention}")
        embed.add_field(name="Reason:", value=reason, inline=False)
        if ptype != 'Warning' and ptype != 'Blacklist':
            embed.set_footer(text="Expires")
            embed.timestamp = duration
        if ptype == 'Blacklist':
            embed.set_thumbnail(url='https://media3.giphy.com/media/H99r2HtnYs492/giphy.gif')
        if ptype == 'Suspension' and guild.id == 703987028567523468:
            embed.set_thumbnail(url='https://i.imgur.com/ZDuZLx8.gif')
        await channel.send(embed=embed)
        await user.send(f"{ptype} in {guild.name} | {user.mention}", embed=embed)

def setup(client):
    client.add_cog(Punishments(client))

def duration_formatter(tsecs, ptype):
    days, remainder = divmod(tsecs, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    seconds = round(seconds)
    fduration = f"This {ptype} was issued for "
    if days != 0:
        fduration += f"{int(days)} Days, "
    if hours != 0:
        fduration += f"{int(hours)} Hours, "
    if minutes != 0:
        fduration += f"{int(minutes)} Minutes, "
    fduration += f"{int(seconds)} Seconds."
    return fduration

async def send_update_embeds(client, guild, member, mute, auto=True, requester=None, reason=None):
    ptype = "Un-muted" if mute else "Un-suspended"
    desc = f"{member.mention} was "
    desc += f"automatically {ptype}." if auto else f"manually {ptype} by {requester.mention} because:\n {reason}."
    embed = discord.Embed(title=f"{ptype} Info", description=desc, color=discord.Color.green())
    time = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    embed.add_field(name="Info:", value=f"{ptype} at: {time}", inline=False)
    embed.set_footer(text=f"Member Successfully {ptype}!")
    channel = client.guild_db.get(guild.id)[sql.gld_cols.punishlogchannel]
    await channel.send(embed=embed)
    await member.send(member.mention, embed=embed)

async def unmute(pool, guild, member):
    for channel in guild.text_channels:
        permissions = channel.permissions_for(member)
        if permissions.read_messages:
            await channel.set_permissions(member, overwrite=None)
    await sql.set_unactive(pool, guild.id, member.id, 'mute')


async def unsuspend(pool, guild, suspend_role, verifiedrole, member, roles):
    await member.remove_roles(suspend_role)
    roles.append(verifiedrole)
    for r in roles:
        await member.add_roles(r)
    await sql.set_unactive(pool, guild.id, member.id, 'suspend')

async def punishment_handler(client, guild, member, ptype, tsecs, roles=None):
    try:
        await asyncio.sleep(tsecs)
        # TODO: check if still active
        if ptype == 'mute':
            await unmute(client.pool, guild, member)
            await send_update_embeds(client, guild, member, True)
        elif ptype == 'suspend':
            suspendrole = client.guild_db.get(guild.id)[sql.gld_cols.suspendedrole]
            verifiedrole = client.guild_db.get(guild.id)[sql.gld_cols.verifiedroleid]
            await unsuspend(client.pool, guild, suspendrole, verifiedrole, member, roles)
            await send_update_embeds(client, guild, member, False)
    except asyncio.CancelledError:
        pass
