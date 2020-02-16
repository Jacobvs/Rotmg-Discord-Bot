import os
import time
import json

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('DISCORD_TOKEN')

def get_prefix(client, message):
    with open('data/prefixes.json', 'r') as file:
        prefixes = json.load(file)

    return prefixes[str(message.guild.id)]


bot = commands.Bot(command_prefix = get_prefix)

@bot.command()
async def load(ctx, extension):
    extension = extension.lower()
    bot.load_extension(f'cogs.{extension}')


@bot.command()
async def unload(ctx, extension):
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')


@bot.command()
async def reload(ctx, extension):
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    await ctx.send('{} has been reloaded.'.format(extension.capitalize()))


for filename in os.listdir('./cogs/'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


#Checks
allowed_role_ids = {678543120119365671} #Admin,

@bot.check
async def global_perms_check(ctx):
    author_roles = [role.id for role in ctx.author.roles]
    if len(allowed_role_ids.intersection(author_roles)):
        return True
    msg = await ctx.send('{} Does not have the perms to use this command'.format(ctx.author.mention), delete_after=1.5)
    time.sleep(0.5)
    await ctx.message.delete()


bot.run(token)