import json
import logging
import os
import aiomysql
import urllib3
import discord
from discord.ext import commands
from dotenv import load_dotenv

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
urllib3.disable_warnings()

load_dotenv()
token = os.getenv('DISCORD_TOKEN')


def get_prefix(client, message):
    """Returns the prefix for the specified server"""
    if message.guild is None:
        return "!"

    with open('data/prefixes.json', 'r') as f:
        prefixes = json.load(f)

    return prefixes[str(message.guild.id)]


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')
bot.owner_id = 196282885601361920


@bot.event
async def on_ready():
    """Wait until bot has connected to discord, then create MySQL Connection pool"""
    bot.pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"), port=3306, user='root', password=os.getenv("MYSQL_PASSWORD"),
        db='mysql', loop=bot.loop)
    await bot.change_presence(status=discord.Status.online, activity=discord.Game("boooga."))
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(usage="!load [cog]")
@commands.is_owner()
async def load(ctx, extension):
    """Load specified cog"""
    extension = extension.lower()
    bot.load_extension(f'cogs.{extension.capitalize()}')


@bot.command(usage="!unload [cog]")
@commands.is_owner()
async def unload(ctx, extension):
    """Unload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension.capitalize()}')


@bot.command(usage="!reload [cog]")
@commands.is_owner()
async def reload(ctx, extension):
    """Reload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    await ctx.send('{} has been reloaded.'.format(extension.capitalize()))


for filename in os.listdir('./cogs/'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')


# Error Handlers
@bot.event
async def on_error(event, *args, **kwargs):
    """Log errors for debugging"""
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            f.write(f'Unhandled error: {args[0]}\n')


# Checks
with open('data/variables.json', 'r') as file:
    variables = json.load(file)

# @bot.check
# async def global_perms_check(ctx):
#     # if await bot.is_owner(ctx.author):
#     #     print(ctx.__dict__)
#     #     await ctx.invoke(ctx.command)
#     #     return False
#     return True

bot.run(token)
