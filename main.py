import datetime
import importlib
import json
import logging
import os
from sys import modules

import aiomysql
import discord
import urllib3
from discord.ext import commands
from dotenv import load_dotenv

import sql
from cogs import punishments
from cogs.logging import update_leaderboards

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)
urllib3.disable_warnings()

global PRELOADED_MODULES
# sys and importlib are ignored here too
PRELOADED_MODULES = set(modules.values())

load_dotenv()
token = os.getenv('DISCORD_TOKEN')
gh_token = os.getenv('GITHUB_TOKEN')
nebula_token = os.getenv('NEBULA_TOKEN')
is_testing = os.getenv('TESTING')
is_testing = True if is_testing == '1' else False


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
bot.gh_token = gh_token
bot.nebula_token = nebula_token
with open('data/variables.json', 'r') as file:
    bot.maintenance_mode = json.load(file).get("maintenance_mode")


@bot.event
async def on_ready():
    """Wait until bot has connected to discord"""
    bot.pool = await aiomysql.create_pool(host=os.getenv("MYSQL_HOST"), port=3306, user='jacobvs', password=os.getenv("MYSQL_PASSWORD"),
                                          db='mysql', loop=bot.loop, connect_timeout=60)
    bot.start_time = datetime.datetime.now()
    bot.raid_db = {}
    bot.mapmarkers = {}
    bot.players_in_game = []
    bot.active_raiders = {}
    bot.serverwleaderboard = [660344559074541579, 703987028567523468, 739573333242150975, 691607211046076471, 719406991117647893, 713655609760940044]
    await build_guild_db()
    for g in bot.guild_db:
        bot.raid_db[g] = {"afk": {}, "cp": {}, "leaders": []}

    if bot.maintenance_mode:
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game("IN MAINTENANCE MODE!"))
    else:
        await bot.change_presence(status=discord.Status.online, activity=discord.Game("!patreon | !modmail"))
    bot.loop.create_task(update_leaderboards(bot))

    bot.active_punishments = {}

    if not is_testing:
        active = await sql.get_all_active_punishments(bot.pool)
        for p in active:
            guild = bot.get_guild(p[sql.punish_cols.gid])
            if guild:
                member = guild.get_member(p[sql.punish_cols.uid])
                if member:
                    ptype = p[sql.punish_cols.type]
                    until = p[sql.punish_cols.endtime]
                    tsecs = (until - datetime.datetime.utcnow()).total_seconds()
                    if ptype == 'suspend':
                        roles = await sql.get_suspended_roles(bot.pool, member.id, guild)
                        t = bot.loop.create_task(punishments.punishment_handler(bot, guild, member, ptype, tsecs, roles))
                    else:
                        t = bot.loop.create_task(punishments.punishment_handler(bot, guild, member, ptype, tsecs))
                    bot.active_punishments[str(guild.id)+str(member.id)+ptype] = t

    init_queues()
    bot.in_queue = {0: [], 1: []}
    guild = bot.get_guild(660344559074541579)
    bot.patreon_role = guild.get_role(736954974545641493)
    pdata = await sql.get_all_patreons(bot.pool)
    lst = [r[0] for r in pdata]
    bot.patreon_ids = set(lst)

    bot.beaned_ids = set([])
    print(f'{bot.user.name} has connected to Discord!')

async def build_guild_db():
    bot.guild_db = await sql.construct_guild_database(bot.pool, bot)

# Link queue to raiding category (queue_channel, category)
# 1. Dungeoneer (oryx raiding `Queue`)
queue_links = [(660347818061332481, 660347478620766227), (736226011733033041, 736220007356432426)]
def init_queues():
    bot.queue_links = {}
    bot.queues = {}
    bot.morder = {}
    for i in queue_links:
        queue = bot.get_channel(i[0])
        bot.queues[i[0]] = []

        for m in queue.members:
            bot.queues[i[0]].append(m.id)

        category = bot.get_channel(i[1])

        bot.queue_links[queue.id] = (queue, category)
        bot.queue_links[category.id] = (queue, category)
    for g in bot.guilds:
        bot.morder[g.id] = {'npriority': 0, 'nnormal': 0, 'nvc': 0}


@bot.command(usage="resetqueues")
@commands.is_owner()
async def resetqueues(ctx):
    init_queues()


@bot.command(usage="load <cog>")
@commands.is_owner()
async def load(ctx, extension):
    """Load specified cog"""
    extension = extension.lower()
    bot.load_extension(f'cogs.{extension}')
    await ctx.send('{} has been loaded.'.format(extension.capitalize()))


@bot.command(usage="unload <cog>")
@commands.is_owner()
async def unload(ctx, extension):
    """Unload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')
    await ctx.send('{} has been unloaded.'.format(extension.capitalize()))


@bot.command(usage="reload <cog/guilds/utils/all>")
@commands.is_owner()
async def reload(ctx, extension):
    """Reload specified cog"""
    extension = extension.lower()
    if extension == 'guilds':
        await build_guild_db()
        extension = 'Guild Database'
    elif extension == 'all':
        import sql
        importlib.reload(sql)
        import utils
        importlib.reload(utils)
        import checks
        importlib.reload(checks)
        import embeds
        importlib.reload(embeds)
        import cogs.Minigames.blackjack
        importlib.reload(cogs.Minigames.blackjack)
        import cogs.Minigames.coinflip
        importlib.reload(cogs.Minigames.coinflip)
        import cogs.Minigames.connect4
        importlib.reload(cogs.Minigames.connect4)
        import cogs.Minigames.hangman
        importlib.reload(cogs.Minigames.hangman)
        import cogs.Minigames.highlow
        importlib.reload(cogs.Minigames.highlow)
        import cogs.Minigames.roulette
        importlib.reload(cogs.Minigames.roulette)
        import cogs.Minigames.russianroulette
        importlib.reload(cogs.Minigames.russianroulette)
        import cogs.Minigames.slots
        importlib.reload(cogs.Minigames.slots)
        import cogs.Minigames.tictactoe
        importlib.reload(cogs.Minigames.tictactoe)
        import cogs.Raiding.afk_check
        importlib.reload(cogs.Raiding.afk_check)
        import cogs.Raiding.fametrain
        importlib.reload(cogs.Raiding.fametrain)
        import cogs.Raiding.headcount
        importlib.reload(cogs.Raiding.headcount)
        import cogs.Raiding.realmclear
        importlib.reload(cogs.Raiding.realmclear)
        import cogs.Raiding.vc_select
        importlib.reload(cogs.Raiding.vc_select)
        bot.reload_extension('cogs.casino')
        bot.reload_extension('cogs.core')
        bot.reload_extension('cogs.error')
        bot.reload_extension('cogs.logging')
        bot.reload_extension('cogs.minigames')
        bot.reload_extension('cogs.misc')
        bot.reload_extension('cogs.moderation')
        bot.reload_extension('cogs.punishments')
        bot.reload_extension('cogs.raiding')
        bot.reload_extension('cogs.verification')
    elif extension == 'utils':
        import sql
        importlib.reload(sql)
        import utils
        importlib.reload(utils)
        import checks
        importlib.reload(checks)
        import embeds
        importlib.reload(embeds)
    elif extension == 'raiding':
        bot.reload_extension('cogs.raiding')
        import cogs.Raiding.afk_check
        importlib.reload(cogs.Raiding.afk_check)
        import cogs.Raiding.fametrain
        importlib.reload(cogs.Raiding.fametrain)
        import cogs.Raiding.headcount
        importlib.reload(cogs.Raiding.headcount)
        import cogs.Raiding.realmclear
        importlib.reload(cogs.Raiding.realmclear)
        import cogs.Raiding.vc_select
        importlib.reload(cogs.Raiding.vc_select)
    elif extension == 'logging':
        bot.reload_extension('cogs.logging')
        import cogs.Raiding.logrun
        importlib.reload(cogs.Raiding.logrun)
    elif extension == 'casino':
        bot.reload_extension('cogs.casino')
        import cogs.Minigames.blackjack
        importlib.reload(cogs.Minigames.blackjack)
        import cogs.Minigames.coinflip
        importlib.reload(cogs.Minigames.coinflip)
        import cogs.Minigames.connect4
        importlib.reload(cogs.Minigames.connect4)
        import cogs.Minigames.hangman
        importlib.reload(cogs.Minigames.hangman)
        import cogs.Minigames.highlow
        importlib.reload(cogs.Minigames.highlow)
        import cogs.Minigames.roulette
        importlib.reload(cogs.Minigames.roulette)
        import cogs.Minigames.russianroulette
        importlib.reload(cogs.Minigames.russianroulette)
        import cogs.Minigames.slots
        importlib.reload(cogs.Minigames.slots)
        import cogs.Minigames.tictactoe
        importlib.reload(cogs.Minigames.tictactoe)
    else:
        bot.reload_extension(f'cogs.{extension}')
    await ctx.send('{} has been reloaded.'.format(extension.capitalize()))



# def rreload(module, paths=None, mdict=None):
#     """Recursively reload modules."""
#     if paths is None:
#         paths = ['']
#     if mdict is None:
#         mdict = {}
#     if module not in mdict:
#         # modules reloaded from this module
#         mdict[module] = []
#     reload(module)
#     for attribute_name in dir(module):
#         attribute = getattr(module, attribute_name)
#         if type(attribute) is ModuleType:
#             if attribute not in mdict[module]:
#                 if attribute.__name__ not in sys.builtin_module_names:
#                     if os.path.dirname(attribute.__file__) in paths:
#                         mdict[module].append(attribute)
#                         rreload(attribute, paths, mdict)
#     reload(module)


@bot.command(usage="fleave <id>")
@commands.is_owner()
async def fleave(ctx, id: int):
    server = bot.get_guild(id)
    await server.leave()
    await ctx.send(f"Ooga-Booga has left {server.name}")

@bot.command(usage="maintenance")
@commands.is_owner()
async def maintenance(ctx):
    if bot.maintenance_mode:
        bot.maintenance_mode = False
        await bot.change_presence(status=discord.Status.online, activity=discord.Game("!patreon | !modmail"))
        await ctx.send("Maintenance mode has been turned off!")
    else:
        bot.maintenance_mode = True
        await bot.change_presence(status=discord.Status.idle, activity=discord.Game("IN MAINTENANCE MODE!"))
        # with open('data/queues.pkl', 'wb') as file:
        #     pickle.dump(bot.queues, file, pickle.HIGHEST_PROTOCOL)
        #
        # print('Saved queue to file')
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

@bot.command(usage='syncm')
@commands.is_owner()
@commands.guild_only()
async def syncm(ctx):
    verified_role = bot.guild_db.get(ctx.guild.id)[sql.gld_cols.verifiedroleid]
    m_names = []
    #(id, ign, 'verified', ctx.guild.name, alt1, alt2)
    async for m in ctx.guild.fetch_members():
        if verified_role in m.roles:
            if m.nick:
                name = None
                alt1 = None
                alt2 = None
                if " | " in m.nick:
                    ns = m.nick.split(" | ")
                    for n in ns:
                        if not name:
                            name = "".join([c for c in n if c.isalpha()])
                        elif not alt1:
                            alt1 = "".join([c for c in n if c.isalpha()])
                        elif not alt2:
                            alt2 = "".join([c for c in n if c.isalpha()])
                else:
                    name = "".join([c for c in m.nick if c.isalpha()])
                m_names.append((m.id, name, 'verified', ctx.guild.name, alt1, alt2))

    await ctx.send(f'Created {len(m_names)} member profiles... Awaiting insertion into DB...')

    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            s = f"Replace INTO rotmg.users (id, ign, status, verifiedguilds, alt1, alt2) VALUES (%s, %s, %s, %s, %s, %s)"
            await cursor.executemany(s, m_names)
            await conn.commit()

    await ctx.send(f'Inserted {len(m_names)} members into DB. Success.')





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
        if await bot.is_owner(ctx.author):
            return True
        embed = discord.Embed(title="Error!", description="Ooga-booga has been put into maintenance mode by the developer! "
                                "This means bugs are being fixed or new features are being added.\n"
                                "Please be patient and if this persists for too long, contact <@196282885601361920>.",
                              color=discord.Color.orange())
        await ctx.send(embed=embed)
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
