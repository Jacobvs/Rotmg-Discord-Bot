import os
import json
import traceback
from discord.ext import commands
from dotenv import load_dotenv
import logging

logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

load_dotenv()
token = os.getenv('DISCORD_TOKEN')


def get_prefix(client, message):
    if message.guild is None:
        return "!"

    with open('data/prefixes.json', 'r') as file:
        prefixes = json.load(file)

    return prefixes[str(message.guild.id)]


bot = commands.Bot(command_prefix=get_prefix)
bot.remove_command('help')


@bot.command(usage="!load [cog]")
async def load(ctx, extension):
    """Load specified cog"""
    extension = extension.lower()
    bot.load_extension(f'cogs.{extension.capitalize()}')


@bot.command(usage="!unload [cog]")
async def unload(ctx, extension):
    """Unload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension.capitalize()}')


@bot.command(usage="!reload [cog]")
async def reload(ctx, extension):
    """Reload specified cog"""
    extension = extension.lower()
    bot.unload_extension(f'cogs.{extension}')
    bot.load_extension(f'cogs.{extension}')
    await ctx.send('{} has been reloaded.'.format(extension.capitalize()))


for filename in os.listdir('./cogs/'):
    if filename.endswith('.py'):
        bot.load_extension(f'cogs.{filename[:-3]}')

#Error Handlers
@bot.event
async def on_command_error(ctx, error):
    if hasattr(ctx.command, "on_error"):
        return  # Don't interfere with custom error handlers

    error = getattr(error, "original", error)  # get original error

    if isinstance(error, commands.CommandNotFound):
        await ctx.message.delete()
        return await ctx.send(f"That command does not exist. Please use `{await bot.get_prefix(ctx.message)}help` for "
                              f"a list of commands.", delete_after=4)

    if isinstance(error, commands.MissingPermissions):
        await ctx.message.delete()
        return await ctx.send(f'{ctx.author.mention} Does not have the perms to use this: `{ctx.command.name}` command.', delete_after=4)

    if isinstance(error, commands.MissingRole):
        await ctx.message.delete()
        return await ctx.send(f'{ctx.author.mention}: ' + str(error), delete_after=4)

    if isinstance(error, commands.NoPrivateMessage):
        return await ctx.send("This command cannot be used in a DM.")

    if isinstance(error, commands.CheckFailure):
        await ctx.message.delete()
        return

    if isinstance(error, commands.CommandError):
        return await ctx.send(
            f"Error executing command `{ctx.command.name}`: {str(error)}")

    await ctx.send("An unexpected error occurred while running that command.")
    logging.warning("Ignoring exception in command {}:".format(ctx.command))
    logging.warning("\n" + "".join(
        traceback.format_exception(
            type(error), error, error.__traceback__)))

@bot.event
async def on_error(event, *args, **kwargs):
    with open('err.log', 'a') as f:
        if event == 'on_message':
            f.write(f'Unhandled message: {args[0]}\n')
        else:
            f.write(f'Unhandled error: {args[0]}\n')

# Checks
with open('data/variables.json', 'r') as file:
    variables = json.load(file)


@bot.check
async def global_perms_check(ctx):
    return True
    # if ctx.message.guild is None:
    #     if ctx.author.id in variables.get('allowed_user_ids'):
    #         return True
    #     return False
    # author_roles = [role.id for role in ctx.author.roles]
    #
    # if len(set(variables.get('allowed_role_ids')).intersection(author_roles)):
    #     return True
    # msg = await ctx.send('{} Does not have the perms to use this command'.format(ctx.author.mention), delete_after=1.5)
    # time.sleep(0.5)
    # await ctx.message.delete()


bot.run(token)