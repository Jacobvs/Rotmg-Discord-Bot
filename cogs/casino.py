import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

import sql
from cogs.Minigames.blackjack import Blackjack
from cogs.Minigames.coinflip import Coinflip

players_in_game = []

class Casino(commands.Cog):

    def __init__(self, client):
        self.client = client


    @commands.command(usage="!blackjack [bet]", aliases=["bj"])
    async def blackjack(self, ctx, bet: int = 0):
        """A single hand of Blackjack.
        The player plays against the dealer (bot) for one hand.
        """
        if ctx.author.id in players_in_game:
            await ctx.message.delete()
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if bet > 0:
            data = await sql.get_casino_player(self.client.pool, ctx.author.id)
            balance = data[sql.casino_cols.balance]
            if balance < bet:
                return await ctx.send(f"You don't have enough credits! Available balance: {balance}")
            if balance >= bet * 2:
                game = Blackjack(ctx, self.client, bet, balance, True)
            else:
                game = Blackjack(ctx, self.client, bet, balance, False)
        else:
            game = Blackjack(ctx, self.client, 0, 0, False)
        players_in_game.append(ctx.author.id)
        await game.play()
        players_in_game.remove(ctx.author.id)

    @commands.command(usage="!coinflip [member] [bet]")
    async def coinflip(self, ctx, member: discord.Member, bet: int):
        """Bet against someone in a classic 50/50"""
        if ctx.author.id in players_in_game:
            await ctx.message.delete()
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if member.bot or member == ctx.author:
            raise commands.BadArgument('Cannot play a game against that member.')
        if bet > 0:
            data = await sql.get_casino_player(self.client.pool, ctx.author.id)
            balance1 = data[sql.casino_cols.balance]
            if balance1 < bet:
                return await ctx.send(f"You don't have enough credits! Available balance: {balance1}")
            data = await sql.get_casino_player(self.client.pool, member.id)
            balance2 = data[sql.casino_cols.balance]
            if balance2 < bet:
                return await ctx.send(f"{member.display_name} doesn't have enough credits to play.")
            game = Coinflip(ctx, self.client, bet, balance1, balance2, member)
            players_in_game.append(ctx.author.id)
            await game.play()
            players_in_game.remove(ctx.author.id)
        else:
            await ctx.message.delete()
            await ctx.send("You have to place a bet higher than 0!")


    @commands.command(usage="!balance {optional: member}", aliases=['bal'])
    async def balance(self, ctx, member: discord.Member=None):
        """Check your balance"""
        if not member:
            member = ctx.author
        if member.bot:
            raise commands.BadArgument('Cannot play a game against that member.')
        data = await sql.get_casino_player(self.client.pool, member.id)
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=member.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Credits", value=f"**{data[sql.casino_cols.balance]:,}** credits.")
        embed.set_footer(text="Use !daily, !work, and !search to get credits.")
        await ctx.send(embed=embed)


    @commands.command(usage="!cooldowns")
    async def cooldowns(self, ctx):
        """Check your cooldowns"""
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        embed = discord.Embed(color=discord.Color.blue())
        str = ""
        for i in range(2, 5):
            str += "Daily: " if i == 2 else "Work: " if i == 3 else "Search: "
            cooldown = data[i]
            if cooldown > datetime.utcnow():
                (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
                str += f"**{hours}:{minutes}:{seconds}**\n"
            else:
                str += " **READY**\n"
        embed.add_field(name="Cooldowns", value=str)
        return await ctx.send(embed=embed)

    @commands.command(usage="!daily")
    async def daily(self, ctx):
        """Claim your daily reward"""
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.dailycooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You have already collected your daily credits!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed)
        balance = data[sql.casino_cols.balance]+2500
        await sql.change_balance(self.client.pool, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.dailycooldown)
        embed.color = discord.Color.green()
        embed.add_field(name="You got 2,500 credits!", value=f"Current balance: **{balance:,}** credits.")
        return await ctx.send(embed=embed)

    @commands.command(usage="!work")
    async def work(self, ctx):
        """Do something...?"""
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.workcooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You're too tired to work again so soon!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed)
        amounts = [500, 750, 800, 1000, 1200, 1300, 1400, 1500, 1700, 2000, 2500, 3000, 5000]
        money = random.choice(amounts)
        balance = data[sql.casino_cols.balance] + money
        await sql.change_balance(self.client.pool, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.workcooldown)
        embed.add_field(name="Work",value=get_job(money),inline=False)
        embed.add_field(name="Balance", value=f"You now have **{balance}** credits.")
        embed.color = discord.Color.green()
        await ctx.send(embed=embed)

    @commands.command(usage="!search")
    async def search(self, ctx):
        """Look around for money"""
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.searchcooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You couldn't find anything!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed)
        amounts = [75, 80, 100, 120, 150, 175, 200, 250, 300, 350, 400]
        money = random.choice(amounts)
        balance = data[sql.casino_cols.balance] + money
        await sql.change_balance(self.client.pool, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.searchcooldown)
        embed.add_field(name="Search", value=f"You found **{money}** credits just lying around!", inline=False)
        embed.add_field(name="Balance", value=f"You now have **{balance}** credits.")
        embed.color = discord.Color.green()
        await ctx.send(embed=embed)


def setup(client):
    client.add_cog(Casino(client))


def timedeltaformatter(tdelta: timedelta):
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return (hours, minutes, seconds)


def get_job(money):
    jobdescriptions = ["You sold your body for **??** credits... Was it worth it?",
                       "You merched on usw2 and gained **??** credits.",
                       "You streamed for 2 hours and made **??** credits.",
                       "You raided DECA and found the loot tables & **??** credits.",
                       "You stole an old ladies purse and found **??** credits.",
                       "You worked a minimum wage job until your soul was dead and got **??** credits.",
                       "You killed Oryx 3 and he dropped **??** credits.",
                       "You made a deal with the devil for **??** credits.",
                       "You drove for uber and made **??** credits."]
    s = random.choice(jobdescriptions)
    s = s.replace("??", f"{money:,}")
    return s

