import asyncio

import discord


class RealmSelect:
    letters = ["🇦", "🇧", "🇨", "🇩", "🇼", "🇽", "🇾", "🇿"]

    def __init__(self, client, ctx, author=None):
        self.client = client
        self.ctx = ctx
        self.author = author if author else ctx.author


    async def start(self):
        # servers = await utils.get_good_realms(self.client, max_pop=15)
        # server_opts = {}
        # if servers:
        #     desc = ""
        #     num = 0
        #     for l in servers[0]:
        #         event = l[3] if l[3] else "N/A"
        #         desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
        #         server_opts[self.letters[num]] = l[0]
        #         num += 1
        #     if not desc:
        #         desc = "No suitable US servers found."
        #     embed = discord.Embed(title="Location Selection", description="Choose a realm or press 🔄 to manually enter a location.", color=discord.Color.gold())
        #     embed.add_field(name="Top US Servers", value=desc, inline=True)
        #     num = 4
        #     desc = ""
        #     for l in servers[1]:
        #         event = l[3] if l[3] else "N/A"
        #         desc += f"{self.letters[num]} - __**{l[0]}**__\n**{l[1]}** People | **{l[2]}** Heroes\n`{event}`\n**{l[4]}** ago\n\n"
        #         server_opts[self.letters[num]] = l[0]
        #         num += 1
        #     if not desc:
        #         desc = "No suitable EU servers found."
        #     embed.add_field(name="Top EU Servers", value=desc, inline=True)
        #     msg = await self.ctx.send(embed=embed)
        #     for r in server_opts:
        #         await msg.add_reaction(r)
        #     await msg.add_reaction("🔄")
        #
        #     def check(react, usr):
        #         return usr == self.author and react.message.id == msg.id and (str(react.emoji) in server_opts.keys() or str(react.emoji) == "🔄")
        #
        #     try:
        #         reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)
        #     except asyncio.TimeoutError:
        #         try:
        #             embed = discord.Embed(title="Timed out!", description="You didn't choose a realm in time!", color=discord.Color.red())
        #             await msg.clear_reactions()
        #             await msg.edit(embed=embed)
        #             return None
        #         except discord.NotFound:
        #             await self.ctx.send("Timed out while selecting channel.")
        #             return None
        #     else:
        #         if str(reaction.emoji) == '🔄':
        #             await msg.delete()
        #             return await self.manual_location()
        #         else:
        #             try:
        #                 await msg.delete()
        #             except discord.Forbidden or discord.NotFound:
        #                 pass
        #             return server_opts[str(reaction.emoji)]
        #
        # else:
        return await self.manual_location(not_found=False)

    async def manual_location(self, not_found=False):
        desc = "No suitable locations were found automatically.\n" if not_found else ""
        desc += "Please enter the location for this run."
        embed = discord.Embed(title="Manual Location Selection", description=desc, color=discord.Color.gold())
        mlocmsg = await self.ctx.send(embed=embed)

        def check(m):
            return m.author == self.author and m.channel == self.ctx.channel

        # Wait for author to select a location
        while True:
            try:
                msg = await self.client.wait_for('message', timeout=1800, check=check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a location in time!", color=discord.Color.red())
                await mlocmsg.clear_reactions()
                await msg.edit(embed=embed)
                return None

            if not ('us' in str(msg.content).lower() or 'eu' in str(msg.content).lower()):
                await self.ctx.send("Please choose a US or EU location!", delete_after=7)
                continue
            else:
                try:
                    await mlocmsg.delete()
                except discord.Forbidden or discord.HTTPException:
                    pass
                return str(msg.content)