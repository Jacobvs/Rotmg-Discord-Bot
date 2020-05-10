import asyncio
import datetime
import random

import discord

import sql
from cogs import casino


class RussianRoulette:

    def __init__(self, ctx, client, bet, player1):
        self.ctx = ctx
        self.client = client
        self.bet = bet
        self.player1 = player1
        self.players = [player1]
        self.killedplayers = []
        self.secondsleft = 60
        self.waiting = True
        self.task = None
        self.gameembed = discord.Embed(title="Russian Roulette", color=discord.Color.gold(),
                                       description=f"**{player1.display_name}** started a game of russian roulette.")\
                                        .add_field(name="Players", value=f"{player1.mention}", inline=False)\
                                        .add_field(name="Time left", value="**60** seconds", inline=False)\
                                        .add_field(name="Bet amount", value=f"**{bet:,}** credits.", inline=True)\
                                        .add_field(name="Pot", value=f"**{bet:,}** credits.", inline=True)\
                                        .set_footer(text="To join, press ✅, to start the game, press ▶️.")
        self.cancelembed = discord.Embed(title="Russian Roulette", color=discord.Color.red())\
                                        .add_field(name="Timed out", value=f"Nobody joined in time. Credits have been refunded.")



    async def play(self):
        self.starttime = datetime.datetime.utcnow()
        self.game_msg = await self.ctx.send(embed=self.gameembed)

        def check(reaction, user):
            if reaction.message.id == self.game_msg.id:
                if str(reaction.emoji) == '✅':
                    return user not in self.players
                if str(reaction.emoji) == "▶":
                    return user.id == self.player1.id
            return False

        await self.game_msg.add_reaction('✅')
        await self.game_msg.add_reaction('▶')

        await asyncio.sleep(0.3)
        self.task = self.client.loop.create_task(self.countdown())

        while self.waiting:
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=self.secondsleft, check=check)

            except asyncio.TimeoutError as e:
                if len(self.players) == 1:
                    self.task.cancel()
                    casino.players_in_game.remove(self.player1.id)
                    await self.game_msg.edit(embed=self.cancelembed)
                    return await self.game_msg.clear_reactions()
                else:
                    self.waiting = False
                    await self.game_msg.clear_reactions()
                    await self.play_game()
                    break

            if str(reaction.emoji) == "▶":
                if len(self.players) == 1:
                    self.task.cancel()
                    casino.players_in_game.remove(self.player1.id)
                    await self.game_msg.edit(embed=self.cancelembed)
                    return await self.game_msg.clear_reactions()
                else:
                    self.waiting = False
                    await self.game_msg.clear_reactions()
                    await self.play_game()
                    break

            data = await sql.get_casino_player(self.client.pool, user.id)
            balance = data[sql.casino_cols.balance]
            if balance < self.bet:
                await self.ctx.send(f"{user.mention} does not have enough credits to join. Available balance: {balance:,}.", delete_after=7)
            elif user.id in casino.players_in_game:
                await self.ctx.send("You're already in a game! "
                                    "Finish that game or wait for it to expire to start a new one.", delete_after=10)
            else:
                self.players.append(user)
                casino.players_in_game.append(user.id)
                mentions = ''.join(p.mention + "\n" for p in self.players)
                self.gameembed.set_field_at(0, name="Players", value=mentions, inline=False)
                self.gameembed.set_field_at(3, name="Pot", value=f"**{(self.bet*len(self.players)):,}** credits.", inline=True)
                await self.game_msg.edit(embed=self.gameembed)


    async def countdown(self):
        count = 0
        while count < 15:
            self.secondsleft = 60 - (datetime.datetime.utcnow() - self.starttime).seconds
            self.gameembed.set_field_at(1, name="Time left", value=f"**{self.secondsleft}** seconds", inline=False)
            await self.game_msg.edit(embed=self.gameembed)
            await asyncio.sleep(4)


    async def play_game(self):
        self.task.cancel()
        self.gameembed.color = discord.Color.blue()
        self.gameembed.set_footer(text="")
        self.gameembed.set_field_at(1, name="Time left", value="Shooting someone in **5** seconds.", inline=False)
        await self.game_msg.edit(embed=self.gameembed)
        await asyncio.sleep(5)
        while True:
            killed = random.choice(self.players)
            self.players.remove(killed)
            self.killedplayers.append(killed)
            mentions = ''.join(p.mention + "\n" for p in self.players)
            mentions += ''.join("~~" + p.mention + "~~ <a:gunfire:707849144378720339>:exploding_head:\n" for p in self.killedplayers)
            self.gameembed.color = discord.Color.red()
            self.gameembed.set_field_at(0, name="Players", value=mentions, inline=False)
            self.gameembed.set_field_at(1, name="Time left", value="Shooting someone in **5** seconds.", inline=False)
            await self.game_msg.edit(embed=self.gameembed)
            if len(self.players) == 1:
                break
            else:
                await asyncio.sleep(1)
                self.gameembed.color = discord.Color.blue()
                await self.game_msg.edit(embed=self.gameembed)
            await asyncio.sleep(4)
        await self.after_game()


    async def after_game(self):
        for p in self.killedplayers:
            data = await sql.get_casino_player(self.client.pool, p.id)
            balance = data[sql.casino_cols.balance]
            await sql.change_balance(self.client.pool, self.ctx.guild.id, p.id, balance-self.bet)
            if p.id in casino.players_in_game: ##Temp bugfix for players not appending properly
                casino.players_in_game.remove(p.id)
        data = await sql.get_casino_player(self.client.pool, self.players[0].id)
        balance = data[sql.casino_cols.balance]
        await sql.change_balance(self.client.pool, self.ctx.guild.id, self.players[0].id, balance + (self.bet*len(self.killedplayers)))
        if self.players[0].id in casino.players_in_game:
            casino.players_in_game.remove(self.players[0].id)
        self.gameembed.color = discord.Color.green()
        self.gameembed.description = f"{self.players[0].mention} won!"
        self.gameembed.remove_field(1)
        self.gameembed.remove_field(1)
        self.gameembed.set_field_at(1, name="Winnings", value=f"**+{(self.bet*(len(self.killedplayers)+1)):,}** credits.")
        await self.game_msg.edit(content=f"{self.players[0].mention}", embed=self.gameembed)