import asyncio
import random

import discord

import sql


class Roulette:

    def __init__(self, ctx, client, bet, player, balance, bet_type):
        self.ctx = ctx
        self.client = client
        self.bet = bet
        self.player = player
        self.bet_type = bet_type
        self.balance = balance

        self.gameembed = discord.Embed(description="Roulette", color=discord.Color.gold()).set_author(name=self.ctx.author.display_name,
                                        icon_url=self.ctx.author.avatar_url).add_field(name="Bet", value=f"**{self.bet:,}** credits.",
                                        inline=True).add_field(name="Placement", value=get_placement(self.bet_type), inline=True)\
                                        .add_field(name="Wheel", value="Rolling in **3**...", inline=False)


    async def play(self):
        self.game_msg = await self.ctx.send(embed=self.gameembed)
        await asyncio.sleep(1)
        count = 0
        while count < 3:
            count += 1
            self.gameembed.set_field_at(2, name="Wheel", value=f"Rolling in **{3-count}**...", inline=False)
            await self.game_msg.edit(embed=self.gameembed)
            await asyncio.sleep(1)

        num = random.randint(-1, 36)
        if num == -1:
            num = 0
        #embed = discord.Embed(title="Rolling!", color=discord.Color.teal()).set_image(url=utils.RouletteGifs[f'_{num}'].value)
        #await self.game_msg.edit(embed=embed)

        multiplier = get_result(num, self.bet_type)
        if multiplier != -1:
            res = f"Rolled **{num}**! - You won!"
            profit = f"**+{self.bet*multiplier:,}** credits."
        else:
            res = f"Rolled **{num}**! - You lost!"
            profit = f"**-{self.bet:,}** credits."

        self.gameembed.set_field_at(2, name="Wheel", value=res, inline=False)
        self.gameembed.add_field(name="Profit", value=profit, inline=False)
        self.gameembed.add_field(name="Balance", value=f"**{self.balance+(self.bet*multiplier):,}** credits.")
        self.gameembed.color = get_color(num)
        await sql.change_balance(self.client.pool, self.ctx.guild.id, self.player.id, self.balance+(self.bet*multiplier))

        #await asyncio.sleep(12)
        await self.game_msg.edit(embed=self.gameembed)


def get_result(num, bet_type: str):
    if bet_type == "black":
        if num in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]:
            return 1
    elif bet_type == 'red':
        if num in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
            return 1
    elif bet_type == "green" and num == 0:
        return 18
    elif bet_type == "high" and num >= 19:
        return 1
    elif bet_type == "low" and 18 >= num >= 1:
        return 1
    elif bet_type == "even" and num % 2 == 0 and num != 0:
        return 1
    elif bet_type == "odd" and num % 2 != 0:
        return 1
    elif bet_type.isdigit():
        if int(bet_type) == num:
            return 35
    return -1

def get_color(num):
    if num in [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]:
        return discord.Color.from_rgb(0, 0, 0)
    elif num in [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]:
        return discord.Color.red()
    else:
        return discord.Color.green()

def get_placement(bet_type: str):
    placements = {
        "red": "Red (Bet **x2**)",
        "black": "Black (Bet **x2**)",
        "green": "Green (Bet **x18**)",
        "high": "High (Bet **x2**)",
        "low": "Low (Bet **x2**)",
        "even": "Even (Bet **x2**)",
        "odd": "Odd (Bet **x2**)"
    }
    if bet_type.isdigit():
        return f"Number {bet_type} - Bet x35"
    else:
        return placements.get(bet_type)
