import json
import logging
import os

import aiomysql
import discord
import urllib3
from discord.ext import commands
from dotenv import load_dotenv

import sql

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


bot = commands.Bot(command_prefix='!')
bot.remove_command('help')
bot.owner_id = 196282885601361920
with open('data/variables.json', 'r') as file:
    bot.maintenance_mode = json.load(file).get("maintenance_mode")


@bot.event
async def on_ready():
    """Wait until bot has connected to discord"""
    bot.pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"), port=3306, user='root', password=os.getenv("MYSQL_PASSWORD"),
                                          db='mysql', loop=bot.loop)
    bot.guild_db = await sql.construct_guild_database(bot.pool, bot)
    bot.raid_db = {}
    bot.mapmarkers = {}
    for g in bot.guild_db:
        bot.raid_db[g] = {"raiding": {0: None, 1: None, 2: None}, "vet": {0: None, 1: None}, "events": {0: None, 1: None}, "leaders": []}

    if bot.maintenance_mode:
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game("IN MAINTENANCE MODE!"))
    else:
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

@bot.command(usage="!fleave <id>")
@commands.is_owner()
async def fleave(ctx, id: int):
    server = bot.get_guild(id)
    await server.leave()
    await ctx.send(f"Ooga-Booga has left {server.name}")

@bot.command(usage="!maintenance")
@commands.is_owner()
async def maintenance(ctx):
    if bot.maintenance_mode:
        bot.maintenance_mode = False
        await ctx.send("Maintenance mode has been turned off!")
    else:
        bot.maintenance_mode = True
        await ctx.send("Maintenance mode has been turned on!")
    with open("data/variables.json", 'r+') as f:
        data = json.load(f)
        data["maintenance_mode"] = bot.maintenance_mode
        f.seek(0)
        json.dump(data, f)
        f.truncate()

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
@bot.check
async def maintenance_mode(ctx):
    if bot.maintenance_mode:
        if ctx.guild.id == 678528908429361152:
            return True
        embed = discord.Embed(title="Error!", description="Ooga-booga has been put into maintenance mode by the developer! "
                                "This means bugs are being fixed or new features are being added.\n"
                                "Please be patient and if this persists for too long, contact <@196282885601361920>.",
                              color=discord.Color.orange())
        await ctx.send(embed=embed, delete_after=6)
        return False
    return True

# @bot.check
# async def global_perms_check(ctx):
#     # if await bot.is_owner(ctx.author):
#     #     print(ctx.__dict__)
#     #     await ctx.invoke(ctx.command)
#     #     return False
#     return True

bot.run(token)
