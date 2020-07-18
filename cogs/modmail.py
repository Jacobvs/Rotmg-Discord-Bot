import asyncio
import datetime

import discord
from discord.ext import commands

import utils


class Modmail(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(usage='modmail', description='Send a modmail.', aliases=['mail', 'mod'])
    @commands.is_owner()
    async def modmail(self, ctx):
        mail_message = ModmailMessage(self.client, ctx)
        await mail_message.start()


def setup(client):
    client.add_cog(Modmail(client))


class ModmailMessage:
    def __init__(self, client, ctx):
        self.client = client
        self.ctx = ctx
        self.numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']

    async def start(self):
        if not self.ctx.guild:
            servers = []
            for g in self.client.guilds:
                if g.get_member(self.ctx.author.id):
                    servers.append(g)
            serverstr = ""
            for i, s in enumerate(servers[:10]):
                serverstr += self.numbers[i] + " - " + s.name + "\n"
            embed = discord.Embed(description="What server would you like to send modmail to?\n" + serverstr,
                                  color=discord.Color.gold())
            msg = await self.ctx.author.send(embed=embed)
            for e in self.numbers[:len(servers)]:
                await msg.add_reaction(e)

            def check(react, usr):
                return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in self.numbers[:len(servers)]

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose a server in time!",
                                      color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            server = servers[self.numbers.index(str(reaction.emoji))]
            await msg.delete()

        else:
            try:
                await self.ctx.message.delete()
            except discord.NotFound:
                pass
            server = self.ctx.guild

        embed = discord.Embed(title="Is the modmail about a specific member?", description="If this message is "
                            "regarding someone in the server, please react to the ✅ emoji, otherwise react to the ❌.",
                            color=discord.Color.gold())
        try:
            msg = await self.ctx.author.send(embed=embed)
            dmchannel = msg.channel
        except discord.Forbidden:
            return await self.ctx.send(f"{self.ctx.author.mention} - You have DM's from server members disabled! Please enable DM's then try again.")

        await msg.add_reaction("✅")
        await msg.add_reaction("❌")

        def check(react, usr):
            return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "❌"]

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
        except asyncio.TimeoutError:
            embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                  color=discord.Color.red())
            await msg.delete()
            return await self.ctx.author.send(embed=embed)

        await msg.delete()

        if str(reaction.emoji) == '✅':
            embed = discord.Embed(title="Please choose a member.", description="To select a member, use one of these formats:\n1. ROTMG IGN\n2.Discord ID\n3. Discord tag & "
                                                                               "descriminator (ex: Darkmatter#7321).", colour=discord.Color.gold())
            msg = await self.ctx.author.send(embed=embed)

            converter = utils.MemberLookupConverter()

            def member_check(m):
                return m.author.id == self.ctx.author.id and m.channel == dmchannel

            while True:
                try:
                    membermsg = await self.client.wait_for('message', timeout=1800, check=member_check)
                except asyncio.TimeoutError:
                    embed = discord.Embed(title="Timed out!", description="You didn't choose a member in time!", color=discord.Color.red())
                    await msg.delete()
                    return await self.ctx.author.send(embed=embed)

                try:
                    aboutmember = await converter.convert(self.ctx, str(membermsg.content), server)
                    try:
                        await msg.delete()
                    except discord.NotFound:
                        pass
                    break
                except discord.ext.commands.BadArgument:
                    await self.ctx.send(f"The member you specified (`{msg.content}`) was not found.", delete_after=7)
        else:
            aboutmember = None

        embed = discord.Embed(title="Describe your issue", description="Send a message with your modmail to this channel. Please be as descriptive as possible & include "
                                                                       "**links** (not attachments) to images/videos of proof if you have them.", color=discord.Color.gold())
        msg = await self.ctx.author.send(embed=embed)

        while True:
            def member_check(m):
                return m.author.id == self.ctx.author.id and m.channel == dmchannel
            try:
                mailmsg = await self.client.wait_for('message', timeout=1800, check=member_check)
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't write your modmail in time!", color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            content = str(mailmsg.content)
            mailembed = discord.Embed(title=f"Modmail from {self.ctx.author.name} -> {server.name}", description="If this looks correct, please press the ✅ to continue, "
                                    "otherwise press the 🔄 emoji to change your message.", color=discord.Color.gold())
            mailembed.add_field(name="Content:", value=content, inline=False)
            if aboutmember:
                mailembed.add_field(name="Regarding:", value=f"This modmail is regarding {aboutmember.name}")
            mailembed.set_footer(text="Modmail written at ")
            mailembed.timestamp = datetime.datetime.utcnow()

            msg = await self.ctx.author.send(embed=mailembed)
            await msg.add_reaction("✅")
            await msg.add_reaction("🔄")

            def check(react, usr):
                return usr.id == self.ctx.author.id and react.message.id == msg.id and str(react.emoji) in ["✅", "🔄"]

            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=1800, check=check)  # Wait 1/2 hr max
            except asyncio.TimeoutError:
                embed = discord.Embed(title="Timed out!", description="You didn't choose an option in time!",
                                      color=discord.Color.red())
                await msg.delete()
                return await self.ctx.author.send(embed=embed)

            if str(reaction.emoji) == '✅':
                break
            else:
                await msg.delete()
                await self.ctx.author.send(embed=embed)







