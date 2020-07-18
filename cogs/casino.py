import asyncio
import random
from datetime import datetime, timedelta

import discord
from discord.ext import commands

import embeds
import sql
import utils
from cogs.Minigames.blackjack import Blackjack
from cogs.Minigames.coinflip import Coinflip
from cogs.Minigames.roulette import Roulette
from cogs.Minigames.russianroulette import RussianRoulette
from cogs.Minigames.slots import Slots


class Casino(commands.Cog):
    """Play various casino games against the bot or another member."""

    def __init__(self, client):
        self.client = client


    @commands.command(usage="blackjack [bet]", aliases=["bj"],
                      description="A single hand of Blackjack.\nThe player plays against the dealer (bot) for one hand.")
    async def blackjack(self, ctx, bet: int = 0):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if ctx.author.id in self.client.players_in_game:
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
        self.client.players_in_game.append(ctx.author.id)
        await game.play()
        self.client.players_in_game.remove(ctx.author.id)

    @commands.command(usage="roulette [bet_type] [bet]", aliases=['r'], description="A classic game of roulette.")
    async def roulette(self, ctx, bet_type: str=None, bet: int=None):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if not bet_type or not bet:
            return await ctx.send(embed=embeds.roulette_help_embed())
        if ctx.author.id in self.client.players_in_game:
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if bet_type.isdigit():
            if int(bet_type) > 36 or int(bet_type) < 1:
                return await ctx.send("Please choose a number between 1-36, or red/black/green/high/low/even/odd.")
        elif bet_type.lower() not in ["red", "black", "green", "high", "low", "even", "odd"]:
            return await ctx.send("Please choose a number between 0-36, or red/black/green/high/low/even/odd.")
        if bet > 0:
            data = await sql.get_casino_player(self.client.pool, ctx.author.id)
            balance = data[sql.casino_cols.balance]
            if balance < bet:
                return await ctx.send(f"You don't have enough credits! Available balance: {balance}")

            game = Roulette(ctx, self.client, bet, ctx.author, balance, bet_type)
        else:
            return await ctx.send("You have to bet more than 0 credits on this game!", delete_after=10)
        self.client.players_in_game.append(ctx.author.id)
        await game.play()
        self.client.players_in_game.remove(ctx.author.id)


    @commands.command(usage="slots [bet]", aliases=['slot', 's'], description="Test your luck on the slot machine!")
    async def slots(self, ctx, bet: int = None):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if not bet:
            return await ctx.send(embed=embeds.slots_help_embed())
        if ctx.author.id in self.client.players_in_game:
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if bet > 0:
            data = await sql.get_casino_player(self.client.pool, ctx.author.id)
            balance = data[sql.casino_cols.balance]
            if balance < bet:
                return await ctx.send(f"You don't have enough credits! Available balance: {balance}")

            game = Slots(self.client, ctx, bet, ctx.author, balance)
        else:
            return await ctx.send("You have to bet more than 0 credits on this game!", delete_after=10)
        self.client.players_in_game.append(ctx.author.id)
        await game.play()
        self.client.players_in_game.remove(ctx.author.id)

    @commands.command(usage="coinflip <member> [bet]", aliases=['cf'], description="Bet against someone in a classic 50/50.")
    async def coinflip(self, ctx, member: utils.MemberLookupConverter, bet: int):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if ctx.author.id in self.client.players_in_game:
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if member.id in self.client.players_in_game:
            return await ctx.send(f"{member.mention} is in a game. Wait for them to finish their game before starting a new one!",
                                  delete_after=10)
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
            self.client.players_in_game.append(ctx.author.id)
            await game.play()
            self.client.players_in_game.remove(ctx.author.id)
        else:
            await ctx.send("You have to place a bet higher than 0!")

    @commands.command(usage="russianroulette <bet>", aliases=['rr'], description="Test your luck by starting a game of russian roulette!")
    async def russianroulette(self, ctx, bet: int):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if ctx.author.id in self.client.players_in_game:
            return await ctx.send("You're already in a game! "
                                  "Finish that game or wait for it to expire to start a new one.", delete_after=10)
        if bet > 0:
            data = await sql.get_casino_player(self.client.pool, ctx.author.id)
            balance = data[sql.casino_cols.balance]
            if balance < bet:
                return await ctx.send(f"You don't have enough credits! Available balance: {balance}")
            game = RussianRoulette(ctx, self.client, bet, ctx.author)
            self.client.players_in_game.append(ctx.author.id)
            await game.play()
        else:
            await ctx.send("You have to place a bet higher than 0!")


    @commands.command(usage="balance [member]", aliases=['bal'], description="Check your casino balance.")
    async def balance(self, ctx, member: utils.MemberLookupConverter=None):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if not member:
            member = ctx.author
        if member.bot:
            raise commands.BadArgument("Bot's don't gamble!")
        data = await sql.get_casino_player(self.client.pool, member.id)
        embed = discord.Embed(color=discord.Color.gold())
        embed.set_author(name=member.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Balance", value=f"**{data[sql.casino_cols.balance]:,}** credits.")
        embed.set_footer(text="Use !daily, !work, and !search to get credits.")
        await ctx.send(embed=embed)

    @commands.command(usage="pay <member> <amount> [reason]", description="Pay someone your hard-earned credits.")
    async def pay(self, ctx, member: utils.MemberLookupConverter, amount: int, *reason):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if ctx.author.id in self.client.players_in_game:
            return await ctx.send("You cannot use the pay command while in a game!", delete_after=7)
        elif member.id in self.client.players_in_game:
            return await ctx.send(f"{member.mention} is in a game, retry when they're done!", delete_after=7)
        if member.bot or member == ctx.author:
            raise commands.BadArgument('You cannot pay yourself or bots!')
        if amount <= 0:
            return await ctx.send("Please specify a number larger than 0.")
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        balance1 = data[sql.casino_cols.balance]
        if balance1 < amount:
            return await ctx.send(f"You don't have enough credits! Available balance: {balance1:,}")
        data = await sql.get_casino_player(self.client.pool, member.id)
        balance2 = data[sql.casino_cols.balance]
        await sql.change_balance(self.client.pool, ctx.guild.id, ctx.author.id, balance1-amount)
        await sql.change_balance(self.client.pool, ctx.guild.id, member.id, balance2 + amount)
        embed = discord.Embed(title=":money_with_wings:",color=discord.Color.green())
        embed.add_field(name=f"{ctx.author.display_name} -> {member.display_name}",
                        value=f"Payment of **{amount:,}** credits sent to {member.mention}.")
        if reason:
            res = "".join(w + " " for w in reason)
            embed.add_field(name="Reason", value=res, inline=False)
        await ctx.send(embed=embed)

    @commands.command(usage="steal <member>",
                      description="Your gambling addiction is strong enough to steal from someone?! What is wrong with you?")
    async def steal(self, ctx, member: utils.MemberLookupConverter):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        if member.bot or member == ctx.author:
            raise commands.BadArgument('You cannot steal from yourself or bots!')
        p1_data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = p1_data[sql.casino_cols.stealcooldown]
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed = discord.Embed(color=discord.Color.red())
            embed.add_field(name="You need to lie low so you don't get caught stealing!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed, delete_after=10)
        p1_bal = p1_data[sql.casino_cols.balance]
        if p1_bal < 0:
            return await ctx.send(f"You're in debt and can't steal! Current balance: **{p1_bal:,}** credits.", delete_after=10)
        p2_data = await sql.get_casino_player(self.client.pool, member.id)
        p2_bal = p2_data[sql.casino_cols.balance]
        if p2_bal < 1000:
            return await ctx.send(f"{member.mention} is too poor to be stolen from! Their bank account has **{p2_bal:,}** credits in it.")
        amount = int((p2_bal+p1_bal)*0.1)
        num = random.randint((-amount), amount)
        num = -2000 if num < -2000 else int(p2_bal/2) if num > int(p2_bal/2) else num
        await sql.change_balance(self.client.pool, ctx.guild.id, ctx.author.id, (p1_bal+num))
        await sql.change_balance(self.client.pool, ctx.guild.id, member.id, (p2_bal - num))
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.stealcooldown)
        embed = discord.Embed().set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        if num < 0:
            embed.color = discord.Color.red()
            embed.add_field(name="Steal", value=f"{ctx.author.mention} tried to steal from {member.mention} but was caught!\n"
                                                f"{ctx.author.display_name} was fined **{num:,}** credits – which"
                                                f" were sent to {member.display_name}", inline=False)\
                .add_field(name="Balances", value=f"{ctx.author.mention}: **{(p1_bal+num):,}** credits\n"
                                                  f"{member.mention}: **{(p2_bal-num):,}** credits", inline=False)
            await self.steal_caught(ctx, embed, member)
        else:
            embed.color = discord.Color.green()
            embed.add_field(name="Steal", value=f"{ctx.author.mention} stole **{num:,}** credits from {member.mention}!\n"
                                                f"Are you going to let them get away with that?!", inline=False)\
                .add_field(name="Balances", value=f"{ctx.author.mention}: **{(p1_bal+num):,}** credits\n"
                                                  f"{member.mention}: **{(p2_bal-num):,}** credits", inline=False)
            await ctx.send(content=member.mention, embed=embed)

    async def steal_caught(self, ctx, embed, member):
        msg = await ctx.send(content=member.mention, embed=embed)
        i = 0
        while i < 6:
            i += 1
            embed.color = discord.Color.red() if i %2 == 0 else discord.Color.blue()
            await msg.edit(embed=embed)
            await asyncio.sleep(1)

    @commands.command(usage="top", description="Get the top 10 balances on this server.")
    async def top(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        data = await sql.get_top_balances(self.client.pool, ctx.guild.id)
        top = ""
        for i, r in enumerate(data[1:]):
            if r is None:
                if int((i / 2)) + 1 != 10:
                    top += f"#{int((i/2))+1}-10. No data."
                else:
                    top += "#10. No data."
                break
            if i % 2 == 0:
                top += f"#{int((i/2))+1}. <@{r}> - "
            else:
                top += f"**{r:,}** credits.\n"
        embed = discord.Embed(color=discord.Color.orange()).set_author(name=ctx.guild.name, icon_url=ctx.guild.icon_url)\
                            .add_field(name="Top 10 Balances", value=top)
        await ctx.send(embed=embed)

    @commands.command(usage="cooldowns", description="Check your cooldowns.")
    async def cooldowns(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        embed = discord.Embed(color=discord.Color.blue())
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        str = ""
        for i in range(2, 6):
            str += "Daily: " if i == 2 else "Work: " if i == 3 else "Search: " if i == 4 else "Steal: "
            cooldown = data[i]
            if cooldown > datetime.utcnow():
                (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
                str += f"**{hours}**h, **{minutes}**m, **{seconds}**s\n"
            else:
                str += " **READY**\n"
        embed.add_field(name="Cooldowns", value=str)
        return await ctx.send(embed=embed)

    @commands.command(usage="daily", description="Claim your daily reward.")
    async def daily(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.dailycooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You have already collected your daily credits!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed, delete_after=10)
        balance = data[sql.casino_cols.balance]+7500
        await sql.change_balance(self.client.pool, ctx.guild.id, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.dailycooldown)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.color = discord.Color.green()
        embed.add_field(name="You got 7,500 credits!", value=f"Current balance: **{balance:,}** credits.")
        return await ctx.send(embed=embed)

    @commands.command(usage="work", description="Do something...?")
    async def work(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.workcooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You're too tired to work again so soon!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed, delete_after=10)
        amounts = [500, 750, 800, 1000, 1200, 1300, 1400, 1500, 1700, 2000, 2500, 3000, 5000]
        money = random.choice(amounts)
        balance = data[sql.casino_cols.balance] + money
        await sql.change_balance(self.client.pool, ctx.guild.id, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.workcooldown)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Work",value=get_job(money),inline=False)
        embed.add_field(name="Balance", value=f"You now have **{balance:,}** credits.")
        embed.color = discord.Color.green()
        await ctx.send(embed=embed)

    @commands.command(usage="search", description="Look around for money.")
    async def search(self, ctx):
        try:
            await ctx.message.delete()
        except discord.NotFound:
            pass
        data = await sql.get_casino_player(self.client.pool, ctx.author.id)
        cooldown = data[sql.casino_cols.searchcooldown]
        embed = discord.Embed()
        if cooldown > datetime.utcnow():
            (hours, minutes, seconds) = timedeltaformatter(cooldown - datetime.utcnow())
            embed.color = discord.Color.red()
            embed.add_field(name="You couldn't find anything!", value=f"Next in: {hours}:{minutes}:{seconds}")
            embed.set_footer(text="Use !cooldowns to check your cooldown timers.")
            return await ctx.send(embed=embed, delete_after=10)
        amounts = [75, 80, 100, 120, 150, 175, 200, 250, 300, 350, 400]
        money = random.choice(amounts)
        balance = data[sql.casino_cols.balance] + money
        await sql.change_balance(self.client.pool, ctx.guild.id, ctx.author.id, balance)
        await sql.update_cooldown(self.client.pool, ctx.author.id, sql.casino_cols.searchcooldown)
        embed.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        embed.add_field(name="Search", value=f"You found **{money:,}** credits just lying around!", inline=False)
        embed.add_field(name="Balance", value=f"You now have **{balance:,}** credits.")
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
