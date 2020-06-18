import asyncio
import random

import discord

import sql


class Slots:


    def __init__(self, client, ctx, bet, user, balance):
        self.client = client
        self.ctx = ctx
        self.bet = bet
        self.user = user
        self.winner = False
        self.winnerE = 0
        self.balance = balance
        self.emojis = ['🍋', '🍉', '🍌', '🍒', '💎', '<:slot7:711843601369530458>']
        self.gameembed = discord.Embed(color=discord.Color.blue(), description="Slots").set_author(name=user.display_name,
                                        icon_url=user.avatar_url).add_field(name="Board", value="Setting up...", inline=False)\
                                        .add_field(name="Bet", value=f"**{bet:,}** credits.", inline=False)

    async def play(self):
        self.gamemsg = await self.ctx.send(embed=self.gameembed)
        self.ticket = random.randint(1, 1001)
        self.board = self.rand_board()
        self.mult = 0
        if self.ticket > 848:
            self.winner = True
            num = 0 if self.ticket < 929 else 1 if self.ticket < 957 else 2 if self.ticket < 979 else 3 if self.ticket < 994 \
                else 4 if self.ticket < 998 else 5
            self.winnerE = self.emojis[num]
            self.row = [self.winnerE, self.winnerE, self.winnerE]
            self.mult = 1 if self.ticket < 929 else 2 if self.ticket < 957 else 4 if self.ticket < 979 else 9 if self.ticket < 994 else \
                29 if self.ticket < 998 else 99
            self.winA = int(self.bet*self.mult)
        else:
            self.row = [self.rand_emoji(), self.rand_emoji(), self.rand_emoji()]
            if self.row.count(self.row[0]) == len(self.row):
                choices = self.emojis
                choices.remove(self.row[0])
                self.row[2] = random.choice(choices)

        await self.update_embed()
        await asyncio.sleep(2)
        self.board[0] = self.row[0]
        await self.update_embed()
        await asyncio.sleep(1.4)
        self.board[1] = self.row[1]
        await self.update_embed()
        await asyncio.sleep(1.4)
        self.board[2] = self.row[2]
        await self.update_embed()

        if self.winner is True:
            await sql.change_balance(self.client.pool, self.ctx.guild.id, self.user.id, self.balance+self.winA)
            self.gameembed.color = discord.Color.gold() if self.mult >= 50 else discord.Color.green()
            self.gameembed.description = "Slots - **JACKPOT!**" if self.mult >= 50 else "Slots - **You Won!**"
            self.gameembed.set_field_at(1, name="Bet", value=f"**+{self.winA+self.bet:,}** credits (x{self.mult+1})", inline=False)
            self.gameembed.add_field(name="Balance", value=f"**{self.balance+self.winA:,}** credits.", inline=False)
        else:
            await sql.change_balance(self.client.pool, self.ctx.guild.id, self.user.id, self.balance - self.bet)
            self.gameembed.color = discord.Color.red()
            self.gameembed.description = "Slots - **You lost!**"
            self.gameembed.set_field_at(1, name="Bet", value=f"**-{self.bet:,}** credits", inline=False)
            self.gameembed.add_field(name="Balance", value=f"**{self.balance-self.bet:,}** credits.", inline=False)
        self.gameembed.set_footer(text=f"Your Ticket was {self.ticket}")
        if self.mult >= 50:
            self.gameembed.set_thumbnail(url="https://media3.giphy.com/media/NsAXBSpx0MJ6IBDCPY/source.gif")
            await self.gamemsg.edit(content=f"{self.ctx.author.mention}", embed=self.gameembed)
        else:
            await self.gamemsg.edit(embed=self.gameembed)


    async def update_embed(self):
        s = f"     ––––––––––––––\n | {self.board[0]} | {self.board[1]} | {self.board[2]} |\n––––––––––––––"
        self.gameembed.set_field_at(0, name="Board", value=s)
        await self.gamemsg.edit(embed=self.gameembed)

    def rand_emoji(self):
        return random.choice(self.emojis)

    def rand_board(self):
        return ["<a:slots:711890194801885225>", "<a:slots:711890194801885225>", "<a:slots:711890194801885225>"]