import discord
from discord.ext import commands

from sql import get_guild, gld_cols


async def is_vet_rl_or_higher_check(ctx):
    """Check if user has vet rl or higher roles"""
    guild_db = await get_guild(ctx.bot.pool, ctx.message.guild.id)
    vet_rl_id = guild_db[gld_cols.vetrlroleid]
    return await is_role_or_higher(ctx.message.author, ctx.message.guild, vet_rl_id)


async def is_rl_or_higher_check(ctx):
    """Check if user has rl or higher roles"""
    guild_db = await get_guild(ctx.bot.pool, ctx.message.guild.id)
    rl_id = guild_db[gld_cols.rlroleid]
    return await is_role_or_higher(ctx.message.author, ctx.message.guild, rl_id)


async def is_mm_or_higher_check(ctx):
    """Check if user has map marker or higher roles"""
    guild_db = await get_guild(ctx.bot.pool, ctx.message.guild.id)
    mm_id = guild_db[gld_cols.mmroleid]
    return await is_role_or_higher(ctx.message.author, ctx.message.guild, mm_id)


async def is_role_or_higher(member, guild, roleid):
    """Base check for if user has a role or higher"""
    if member:
        if member.roles:
            member_highest_role_id = member.roles[len(member.roles) - 1].id
            role_ids = list(map(lambda r: r.id, guild.roles))
            index = role_ids.index(roleid)
            if member_highest_role_id in role_ids[index:]:
                return True
        return False
    return False


async def in_voice_channel(ctx):
    """Check if user is in a voice channel"""
    if ctx.author.voice is None:
        await ctx.send("You have to be in a voice channel to use this command.")
        return False
    return True


async def is_dj(ctx):
    """Check if user has a role named 'DJ'"""
    if ctx.message.author.guild_permissions.administrator:
        return True
    role = discord.utils.get(ctx.guild.roles, name="DJ")
    if role in ctx.author.roles:
        return True
    await ctx.message.delete()
    await ctx.say("The 'DJ' Role is required to use this command.", delete_after=4)
    return False


async def audio_playing(ctx):
    """Checks that audio is currently playing before continuing."""
    client = ctx.guild.voice_client
    if client and client.channel and client.source:
        return True
    else:
        raise commands.CommandError("Not currently playing any audio.")


async def in_same_voice_channel(ctx):
    """Checks that the command sender is in the same voice channel as the bot."""
    voice = ctx.author.voice
    bot_voice = ctx.guild.voice_client
    if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
        return True
    else:
        raise commands.CommandError("You need to be in the same voice channel as the bot to use this command.")


async def is_audio_requester(ctx):
    """Checks that the command sender is the song requester."""
    music = ctx.bot.get_cog("Music")
    state = music.get_state(ctx.guild)
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator or state.is_requester(ctx.author):
        return True
    else:
        raise commands.CommandError("You need to be the song requester or an admin to use this command.")
