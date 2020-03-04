import discord
from discord.ext import commands

import sql


async def is_rl_or_higher_check(ctx):
    return await is_rl_or_higher(ctx.message.author, ctx.message.guild)


async def is_rl_or_higher(member, guild):
    if member:
        if member.roles:
            rl_id = sql.get_guild(guild.id)[sql.gld_cols.rlroleid]
            member_highest_role_id = member.roles[len(member.roles) - 1].id
            role_ids = list(map(lambda r: r.id, guild.roles))
            index = role_ids.index(rl_id)
            if member_highest_role_id in role_ids[index:]:
                return True
        return False
    return False

async def is_vet_rl_or_higher_check(ctx):
    return await is_vet_rl_or_higher(ctx.message.author, ctx.message.guild)

async def is_vet_rl_or_higher(member, guild):
    if member:
        if member.roles:
            rl_id = sql.get_guild(guild.id)[sql.gld_cols.vetrlroleid]
            member_highest_role_id = member.roles[len(member.roles) - 1].id
            role_ids = list(map(lambda r: r.id, guild.roles))
            index = role_ids.index(rl_id)
            if member_highest_role_id in role_ids[index:]:
                return True
        return False
    return False


async def in_voice_channel(ctx):
    if ctx.author.voice is None:
        await ctx.send("You have to be in a voice channel to use this command.")
        return False
    return True


async def is_dj(ctx):
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
        raise commands.CommandError(
            "You need to be in the same voice channel as the bot to use this command.")

async def is_audio_requester(ctx):
    """Checks that the command sender is the song requester."""
    music = ctx.bot.get_cog("Music")
    state = music.get_state(ctx.guild)
    permissions = ctx.channel.permissions_for(ctx.author)
    if permissions.administrator or state.is_requester(ctx.author):
        return True
    else:
        raise commands.CommandError(
            "You need to be the song requester or an admin to use this command.")

