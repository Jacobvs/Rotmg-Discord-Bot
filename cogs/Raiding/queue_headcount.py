import discord


class QueueHeadcount:

    def __init(self, client, ctx, hcchannel, raiderrole, rlrole):
        self.client = client
        self.ctx = ctx
        self.hcchannel = hcchannel
        self.raiderrole = raiderrole
        self.rlrole = rlrole


    async def start(self):
        embed = discord.Embed(title='')
        pass
