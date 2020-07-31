import discord
from discord.ext import commands

import sql


def is_bot_owner():
    def predicate(ctx):
        return ctx.author.id == ctx.bot.owner_id
    return commands.check(predicate)


def is_rl_or_higher_check():
    """Check if user has rl or higher roles"""
    def predicate(ctx):
        db = ctx.bot.guild_db.get(ctx.guild.id)
        eventc = db[sql.gld_cols.eventcommandschannel]
        vetc = db[sql.gld_cols.vetcommandschannel]
        role = db[sql.gld_cols.eventrlid] if (eventc and ctx.channel == eventc) else \
                db[sql.gld_cols.vetrlroleid] if (vetc and ctx.channel == vetc) else db[sql.gld_cols.rlroleid]
        return ctx.author.top_role >= role
    return commands.check(predicate)

def is_security_or_higher_check():
    """Check if user has security or higher roles"""
    def predicate(ctx):
        role = ctx.bot.guild_db.get(ctx.guild.id)[sql.gld_cols.securityrole]
        return ctx.author.top_role >= role
    return commands.check(predicate)

def is_mm_or_higher_check():
    """Check if user has map marker or higher roles"""
    def predicate(ctx):
        return ctx.author.top_role >= ctx.bot.guild_db.get(ctx.guild.id)[sql.gld_cols.mmroleid]
    return commands.check(predicate)

def is_role_or_higher(member, role):
    """Base check for if user has a role or higher"""
    if member:
        if member.top_role:
            return member.top_role >= role
        return False
    return False

def manual_verify_channel():
    def predicate(ctx):
        return ctx.channel == ctx.bot.guild_db.get(ctx.guild.id)[sql.gld_cols.manualverifychannel]
    return commands.check(predicate)

def has_manage_roles():
    def predicate(ctx):
        return ctx.author.guild_permissions.manage_roles
    return commands.check(predicate)

def in_voice_channel():
    """Check if user is in a voice channel"""
    def predicate(ctx):
        if ctx.author.voice is None:
            return False
        return True
    return commands.check(predicate)

def not_raiding_vc():
    def predicate(ctx):
        return ctx.author.voice and ctx.author.voice.channel not in ctx.bot.guild_db.get(ctx.guild.id) and "Raid" not in ctx.author.voice.channel.name
    return commands.check(predicate)

def is_dj():
    """Check if user has a role named 'DJ'"""
    def predicate(ctx):
        if ctx.message.author.guild_permissions.administrator:
            return True
        role = discord.utils.get(ctx.guild.roles, name="DJ")
        if role in ctx.author.roles:
            return True
        #await ctx.say("The 'DJ' Role is required to use this command.", delete_after=4)
        return False
    return commands.check(predicate)

# async def audio_playing(ctx):
#     """Checks that audio is currently playing before continuing."""
#     client = ctx.guild.voice_client
#     if client and client.channel and client.source:
#         return True
#     else:
#         raise commands.CommandError("Not currently playing any audio.")
#
# async def in_same_voice_channel(ctx):
#     """Checks that the command sender is in the same voice channel as the bot."""
#     voice = ctx.author.voice
#     bot_voice = ctx.guild.voice_client
#     if voice and bot_voice and voice.channel and bot_voice.channel and voice.channel == bot_voice.channel:
#         return True
#     else:
#         raise commands.CommandError("You need to be in the same voice channel as the bot to use this command.")
#
# async def is_audio_requester(ctx):
#     """Checks that the command sender is the song requester."""
#     music = ctx.bot.get_cog("Music")
#     state = music.get_state(ctx.guild)
#     permissions = ctx.channel.permissions_for(ctx.author)
#     if permissions.administrator or state.is_requester(ctx.author):
#         return True
#     else:
#         raise commands.CommandError("You need to be the song requester or an admin to use this command.")
