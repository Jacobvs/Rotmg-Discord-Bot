import traceback
import logging
from discord.ext import commands


class CommandErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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

        if isinstance(error, commands.CommandError):
            return await ctx.send(f"Unhandled error while executing command `{ctx.command.name}`: {str(error)}")

        await ctx.send("An unexpected error occurred while running that command.")
        logging.warning("Ignoring exception in command {}:".format(ctx.command))
        logging.warning("\n" + "".join(traceback.format_exception(type(error), error, error.__traceback__)))


def setup(client):
    client.add_cog(CommandErrorHandler(client))
