from discord.ext import commands

from cogs.Minigames.blackjack import Blackjack


class Casino(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(usage="!blackjack", aliases=["bj"])
    async def blackjack(self, ctx):
        """A single hand of Blackjack.
        The player plays against the dealer (bot) for one hand.
        """
        game = Blackjack(ctx, self.client)
        await game.play()


def setup(client):
    client.add_cog(Casino(client))
