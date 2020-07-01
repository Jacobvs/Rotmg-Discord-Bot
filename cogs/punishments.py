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

    @commands.command(usage="!warn <@member> <reason>")
    @commands.guild_only()
    @checks.is_rl_or_higher_check()
    async def warn(self, ctx, member: utils.MemberLookupConverter, *, reason):
        """Warn a member for breaking the rules"""
        await sql.add_punishment(self.client.pool, member.id, ctx.guild.id, 'warn', ctx.author.id, None, reason)
        await self.send_log(ctx.guild, member, ctx.author, 'warn', None, reason)
        embed = discord.Embed(title="Success!", description=f"`{member.display_name}` was successfully warned for reason:\n{reason}.",
                              color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage="!mute <@member> <duration> <reason>")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def mute(self, ctx, member: utils.MemberLookupConverter, duration: utils.Duration, *, reason):
        """Prevent the member from sending messages or adding reactions."""
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
        self.client.loop.create_task(punishment_handler(self.client, ctx.guild, member, 'mute', tsecs))

    @commands.command(usage='!unmute <@member> {reason}')
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unmute(self, ctx, member: utils.MemberLookupConverter, *, reason=None):
        """Unmute specified member."""
        if member.bot:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'mute')
        if not already_active:
            return await ctx.send(f'Cannot un-mute `{member.display_name}` as they have no active mutes!')
        await unmute(self.client.pool, ctx.guild, member)
        await send_update_embeds(self.client, ctx.guild, member, True, False, ctx.author, reason)
        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully unmuted.", color=discord.Color.green())
        await ctx.send(embed=embed)

    @commands.command(usage='!suspend <@member> <duration> <reason>')
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def suspend(self, ctx, member: utils.MemberLookupConverter, duration: utils.Duration, *, reason):
        """Suspend a member, assigning them the suspended role."""
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
        self.client.loop.create_task(punishment_handler(self.client, ctx.guild, member, 'suspend', tsecs, roles))


    @commands.command(usage="!unsuspend <@member> {reason}")
    @commands.guild_only()
    @checks.is_security_or_higher_check()
    async def unsuspend(self, ctx, member: utils.MemberLookupConverter, *, reason=None):
        """Unsuspend the specified member."""
        if member.bot:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` (is a bot).')
        if member.guild_permissions.kick_members:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` due to roles.')
        if not reason:
            reason = "No reason specified"
        already_active = await sql.has_active(self.client.pool, member.id, ctx.guild.id, 'suspend')
        if not already_active:
            return await ctx.send(f'Cannot un-suspend `{member.display_name}` as they have no active suspensions!')
        suspendrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.suspendedrole]
        verifiedrole = self.client.guild_db.get(ctx.guild.id)[sql.gld_cols.verifiedroleid]
        roles = await sql.get_suspended_roles(self.client.pool, member.id, ctx.guild)
        await unsuspend(self.client.pool, ctx.guild, suspendrole, verifiedrole, member, roles)
        await send_update_embeds(self.client, ctx.guild, member, False, False, ctx.author, reason)
        embed = discord.Embed(title="Success!",
                              description=f"`{member.display_name}` was successfully un-suspended.", color=discord.Color.green())
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

