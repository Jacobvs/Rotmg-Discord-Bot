import json
from discord.ext import commands


class Checks(commands.Cog):

    def __init__(self, client):
        self.client = client


def setup(client):
    client.add_cog(Checks(client))