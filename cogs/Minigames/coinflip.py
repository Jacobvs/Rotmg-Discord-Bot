import asyncio
import random

import discord
from discord.ext import tasks

import sql


class Coinflip:

    def __init__(self, ctx, client, bet, p1balance, p2balance, player2):
        self.ctx = ctx
        self.client = client
        self.bet = bet
        self.p1balance = p1balance
        self.p2balance = p2balance
        self.player1 = ctx.author
        self.player2 = player2
        self.p1coin = True
        self.startembed = discord.Embed(title="Coinflip", description=f"{self.player2.mention},\n{self.player1.mention} "
                                    "challenged you to a coinflip.", color=discord.Color.orange())\
                                    .add_field(name="Bet Amount", value=f"{bet:,} credits.", inline=False)\
                                    .add_field(name="Time left:", value="You have 90 seconds to accept.", inline=False)\
                                    .set_footer(text=f"React with the ✅ to join, the ❌ to ignore.")
        self.gameembed = discord.Embed(title="Coinflip", color=discord.Color.gold())\
                                    .add_field(name="Player 1", value=f"{self.player1.mention}", inline=True)\
                                    .add_field(name="Player 2", value=f"{self.player2.mention}", inline=True)\
                                    .add_field(name="Coin",value="Setting up game.", inline=False)\
                                    .add_field(name="Bet Amount", value=f"{bet:,} credits.")
        self.flipembed = discord.Embed(title="Flipping!", color=discord.Color.gold())\
                        .set_image(url="https://res.cloudinary.com/darkmattr/image/upload/v1588749311/coinflip_nthewi.gif")


    async def play(self):
        self.game_msg = await self.ctx.send(embed=self.startembed)

        def check(reaction, user):
            valid = (user == self.player2 or (user==self.player1 and str(reaction.emoji) == '❌')) \
                    and reaction.message.id == self.game_msg.id and str(reaction.emoji) in ['✅', '❌']
            return valid

        await self.game_msg.add_reaction('✅')
        await self.game_msg.add_reaction('❌')

        try:
            reaction, user = await self.client.wait_for('reaction_add', timeout=90,  # 90 seconds
                check=check)

        except asyncio.TimeoutError as e:
            self.gameembed.color = discord.Color.red()
            self.gameembed.clear_fields()
            self.gameembed.add_field(name="Timed out", value=f"{self.player2.mention} did not respond in time. Credits have been refunded.")
            await self.game_msg.edit(embed=self.gameembed)
            return await self.game_msg.clear_reactions()

        resp = str(reaction.emoji)
        await self.game_msg.clear_reactions()

        if resp == '✅':
            await self.game_msg.edit(embed=self.gameembed)
            self.p1coin = random.choice([True, False])
            self.countdown.start()
        elif resp == '❌':
            self.gameembed.color = discord.Color.red()
            self.gameembed.clear_fields()
            mention = self.player1.mention if user == self.player1 else self.player2.mention
            self.gameembed.add_field(name="Cancelled", value=f"{mention} did not want to play. Credits have been refunded.")
            await self.game_msg.edit(embed=self.gameembed)


    @tasks.loop(seconds=1.0, count=3)
    async def countdown(self):
        self.gameembed.set_field_at(2, name="Coin", value=f"Flipping in **{3-self.countdown.current_loop}**", inline=False)
        await self.game_msg.edit(embed=self.gameembed)


    @countdown.after_loop
    async def finish_game(self):
        await asyncio.sleep(0.3)
        await self.game_msg.edit(embed=self.flipembed)
        await asyncio.sleep(5.6)
        self.gameembed.color = discord.Color.green()
        self.gameembed.clear_fields()
        if self.p1coin:
            await sql.change_balance(self.client.pool, self.player1.id, self.p1balance + self.bet)
            await sql.change_balance(self.client.pool, self.player2.id, self.p2balance - self.bet)
            self.gameembed.add_field(name="Coin", value=f"\n{self.player1.mention} won **{self.bet}** credits!", inline=False)
            self.gameembed.add_field(name="Balances", value=f"{self.player1.mention} - **{self.p1balance+(self.bet)}**\n"
                                                                  f"{self.player2.mention} - **{self.p2balance-(self.bet)}**")
        else:
            await sql.change_balance(self.client.pool, self.player1.id, self.p1balance - self.bet)
            await sql.change_balance(self.client.pool, self.player2.id, self.p2balance + self.bet)
            self.gameembed.add_field(name="Coin", value=f"{self.player2.mention} won **{self.bet}** credits!", inline=False)
            self.gameembed.add_field(name="Balances", value=f"{self.player1.mention} - **{self.p1balance-(self.bet)}**\n"
                                                                  f"{self.player2.mention} - **{self.p2balance+(self.bet)}**")

        mention = self.player1.mention if self.p1coin else self.player2.mention
        await self.game_msg.edit(content=f"{mention}", embed=self.gameembed)
