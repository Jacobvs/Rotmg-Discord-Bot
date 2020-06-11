import logging
import traceback

import discord
from discord.ext import commands


class CommandErrorHandler(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Handles command errors"""
        if hasattr(ctx.command, "on_error"):
            return  # Don't interfere with custom error handlers

        error = getattr(error, "original", error)  # get original error

        if isinstance(error, commands.CommandNotFound):
            await ctx.message.delete()
            return await ctx.send(f"That command does not exist. Please use `{await bot.get_prefix(ctx.message)}help` for "
                                  f"a list of commands.")

        if isinstance(error, commands.MissingPermissions):
            await ctx.message.delete()
            return await ctx.send(f'{ctx.author.mention} Does not have the perms to use this: `{ctx.command.name}` command.')

        if isinstance(error, commands.MissingRole):
            await ctx.message.delete()
            return await ctx.send(f'{ctx.author.mention}: ' + str(error))

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("This command cannot be used in a DM.")

        if isinstance(error, commands.CheckFailure) or isinstance(error, commands.CheckAnyFailure):
            await ctx.send("You do not have permission to use this command.")
            return await ctx.message.delete()

        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send(
                f"To prevent overload, this command is on cooldown for: ***{round(error.retry_after)}*** more seconds. Retry the command then.",
                delete_after=5)
            return await ctx.message.delete()

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(title="Error!", description="You appear to be missing a required argument!", color=discord.Color.red())
            embed.add_field(name="Missing argument", value=f'`{error.args[0]}`', inline=False)
            embed.add_field(name="Command Usage", value=f'`{ctx.command.usage}`', inline=False)
            if ctx.command.aliases:
                aliases = "".join("!" + c + ", " for c in ctx.command.aliases)
                embed.add_field(name="Command Aliases", value=f"{aliases}", inline=False)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.BadArgument):
            embed = discord.Embed(title="Error!", description="An argument you entered is invalid!", color=discord.Color.red())
            embed.add_field(name="Bad Argument", value=f'`{error.args[0]}`', inline=False)
            embed.add_field(name="Command Usage", value=f'`{ctx.command.usage}`', inline=False)
            if ctx.command.aliases:
                aliases = "`".join("!" + c for c in ctx.command.aliases)+"`"
                embed.add_field(name="Command Aliases", value=f"{aliases}", inline=False)
            return await ctx.send(embed=embed)

        if isinstance(error, commands.CommandError):
            return await ctx.send(f"Unhandled error while executing command `{ctx.command.name}`: {str(error)}")

        if ctx.author.id in self.client.raid_db[ctx.guild.id]['leaders']:
            self.client.raid_db[ctx.guild.id]['leaders'].remove(ctx.author.id)
        await ctx.send("An unexpected error occurred while running that command. Please report this by sending a DM to Darkmattr#7321.")
        logging.warning("Ignoring exception in command {}:".format(ctx.command))
        logging.warning("\n" + "".join(traceback.format_exception(type(error), error, error.__traceback__)))


def setup(client):
    client.add_cog(CommandErrorHandler(client))
