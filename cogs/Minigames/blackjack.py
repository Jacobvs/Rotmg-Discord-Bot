import asyncio

import discord

import sql
from utils import Deck, Hand, Alphabet, Suits


class Blackjack:
    def __init__(self, ctx, bot, bet, balance, can_double):
        self.ctx = ctx
        self.bot = bot
        self.bet = bet
        # Hit or Stand
        self.moves = [Alphabet.H.value, Alphabet.S.value]
        self.deck = Deck()
        self.deck.shuffle()
        self.playing = True

        self.player_hand = Hand()
        self.dealer_hand = Hand()
        self.deck.give_cards(self.player_hand, 2)
        self.deck.give_cards(self.dealer_hand, 2)
        self.player_busted = False
        self.dealer_busted = False
        self.player_won = False
        self.push = False
        self.balance = balance
        self.player_can_double_down = can_double
        self.timeout = False
        if can_double:
            self.moves.append(Alphabet.D.value)

        self.embed = discord.Embed(title=None, type='rich', color=discord.Color.gold(),
        ).set_author(name=self.ctx.author.display_name, icon_url=self.ctx.author.avatar_url_as(static_format='png'), ).add_field(
            name='Blackjack', value=None,  # will be filled later
            inline=False, ).add_field(name='Player\'s Hand', value=None,  # will be filled later
            inline=True, ).add_field(name='Dealer\'s Hand', value=None,  # will be filled after
            inline=True, ).set_footer(text='Hit or Stand?', )
        if bet > 0:
            self.embed.add_field(name='Bet Amount:', value=f"{bet:,}", inline=False)
        if can_double:
            self.embed.set_footer(text='Hit, Stand, or Double Down?', )



    async def play(self):
        self.update_embed('Please wait, setting things up...')
        self.message_game = await self.ctx.send(embed=self.embed)


        def check(reaction, user):
            valid = user == self.ctx.author and reaction.message.id == self.message_game.id and reaction.emoji in self.moves
            return valid


        for move in self.moves:
            await self.message_game.add_reaction(move)

        self.blackjack = False
        # display cards?
        while self.playing:
            # check for blackjacks
            if self.calculate_score(self.player_hand) == 21 and len(self.player_hand) == 2:
                if self.calculate_score(self.dealer_hand) == 21:
                    self.playing = False
                    self.player_won = False
                    self.push = True
                    hint_message = "Push! Both you and the dealer got a Blackjack!"
                else:
                    self.playing = False
                    self.player_won = True
                    self.blackjack = True
                    hint_message = 'Congratulations! You got a Natural Blackjack! (Pays 3:2)'

            elif self.calculate_score(self.player_hand) == 21:
                # give dealer card until total is above 17
                self.playing = False
                while self.calculate_score(self.dealer_hand) < 17:
                    self.deck.give_cards(self.dealer_hand, 1)
                    if self.calculate_score(self.dealer_hand) > 21:
                        self.dealer_busted = True
                        hint_message = ('The dealer busted with a score of '
                                        f'**{self.calculate_score(self.dealer_hand)}**!')
                if self.calculate_score(self.dealer_hand) != 21:
                    self.player_won = True
                    hint_message = 'You Won! You hit Blackjack!'
                else:
                    self.push = True
                    hint_message = 'Push! Both you and the dealer got a Blackjack!'
            # elif self.calculate_score(self.dealer_hand) == 21 and len(self.dealer_hand) == 2:
            #     self.playing = False
            #     self.player_won = False
            #     hint_message = "You lost! The dealer got a Natural Blackjack!"
            else:
                hint_message = ('Your score is '
                                f'**{self.calculate_score(self.player_hand)}**.')
                self.update_embed(hint_message)
                await self.message_game.edit(embed=self.embed)

            # ask player input
                try:
                    reaction, user = await self.bot.wait_for('reaction_add', timeout=3 * 60,  # 3 minutes
                        check=check, )
                except asyncio.TimeoutError as e:
                    # should probably stand if timeout
                    self.playing = False
                    self.timeout = True
                    break

                move = reaction.emoji
                await reaction.remove(user)
                # if hit
                if move == Alphabet.H.value:
                    # give card
                    self.deck.give_cards(self.player_hand, 1)
                    if self.calculate_score(self.player_hand) > 21:
                        self.playing = False
                        self.player_busted = True
                        hint_message = ('You busted with a score of '
                                        f'**{self.calculate_score(self.player_hand)}**.')

                if move == Alphabet.D.value:
                    if (self.player_can_double_down):
                        self.playing = False
                        self.deck.give_cards(self.player_hand, 1)
                        self.bet = self.bet * 2
                        if self.calculate_score(self.player_hand) > 21:
                            self.player_busted = True
                            hint_message = ('You busted with a score of '
                                            f'**{self.calculate_score(self.player_hand)}**.')
                            break
                        while self.calculate_score(self.dealer_hand) < 17:
                            self.deck.give_cards(self.dealer_hand, 1)
                            if self.calculate_score(self.dealer_hand) > 21:
                                self.dealer_busted = True
                                hint_message = ('The dealer busted with a score of '
                                                f'**{self.calculate_score(self.dealer_hand)}**!')
                        if self.calculate_score(self.dealer_hand) > self.calculate_score(self.player_hand) and not self.dealer_busted:
                            hint_message = ('The dealer won! You got '
                                            f'**{self.calculate_score(self.player_hand)}** '
                                            'while the dealer got '
                                            f'**{self.calculate_score(self.dealer_hand)}**.')

                        elif self.calculate_score(self.dealer_hand) < self.calculate_score(self.player_hand) and not self.player_busted:
                            self.player_won = True
                            hint_message = ('You won! You got '
                                            f'**{self.calculate_score(self.player_hand)}** '
                                            'while the dealer got '
                                            f'**{self.calculate_score(self.dealer_hand)}**.')

                        elif self.calculate_score(self.dealer_hand) == self.calculate_score(self.player_hand):
                            self.push = True
                            hint_message = ('Push! You both got '
                                            f'**{self.calculate_score(self.player_hand)}**.')

                # elif stand
                elif move == Alphabet.S.value:
                    # give dealer card until total is above 17
                    while self.calculate_score(self.dealer_hand) < 17:
                        self.deck.give_cards(self.dealer_hand, 1)
                        if self.calculate_score(self.dealer_hand) > 21:
                            self.dealer_busted = True
                            hint_message = ('The dealer busted with a score of '
                                            f'**{self.calculate_score(self.dealer_hand)}**!')

                    if self.calculate_score(self.dealer_hand) > self.calculate_score(self.player_hand) and not self.dealer_busted:
                        hint_message = ('The dealer won! You got '
                                        f'**{self.calculate_score(self.player_hand)}** '
                                        'while the dealer got '
                                        f'**{self.calculate_score(self.dealer_hand)}**.')

                    elif self.calculate_score(self.dealer_hand) < self.calculate_score(self.player_hand) and not self.player_busted:
                        self.player_won = True
                        hint_message = ('You won! You got '
                                        f'**{self.calculate_score(self.player_hand)}** '
                                        'while the dealer got '
                                        f'**{self.calculate_score(self.dealer_hand)}**.')

                    elif self.calculate_score(self.dealer_hand) == self.calculate_score(self.player_hand):
                        self.push = True
                        hint_message = ('Push! You both got '
                                        f'**{self.calculate_score(self.player_hand)}**.')

                    self.playing = False

                if self.timeout:
                    self.update_embed(hint_message="You took to long to choose - so your credits have been refunded.",
                                      money=0, win="+", color=discord.Color.light_grey())
        credits_won = 0
        if self.blackjack:
            credits_won += int(self.bet*1.5)
            self.update_embed(hint_message=hint_message, money=credits_won, win="+", color=discord.Color.green())
        elif self.player_busted or not self.player_won and not self.push and not self.dealer_busted:
            credits_won -= self.bet
            self.update_embed(hint_message=hint_message, money=credits_won, color=discord.Color.red())
        elif self.player_won or self.dealer_busted:
            credits_won += self.bet
            self.update_embed(hint_message=hint_message, money=credits_won, win="+", color=discord.Color.green())
        elif self.push:
            self.update_embed(hint_message=hint_message, money=0, win="+", color=discord.Color.teal())

        if self.bet > 0 and not self.push:
            await sql.change_balance(self.bot.pool, self.ctx.guild.id, self.ctx.author.id, self.balance+credits_won)
        await self.message_game.edit(embed=self.embed)
        await self.message_game.clear_reactions()


    def calculate_score(self, hand):
        hand = hand.cards.copy()
        # put aces at the end
        hand = sorted(hand, key=lambda x: x.rank, reverse=True)
        score = 0
        for card in hand:
            if card.rank > 10:  # a face
                score += 10
            elif card.rank == 1:  # an ace
                if score < 11:
                    score += 11
                else:
                    score += 1
            else:
                score += card.rank
        return score


    def update_embed(self, hint_message, money=None, win="", color=None):
        player_cards = '\n'.join(card.emoji for card in self.player_hand)

        if self.playing:  # hide last card
            dealer_cards = [card.emoji for card in self.dealer_hand.cards[:-1]] + [Suits.JOKER.value]

        else:
            dealer_cards = [card.emoji for card in self.dealer_hand]

        dealer_cards = '\n'.join(dealer_cards)

        if self.bet > 0 and money is not None:
            self.embed.set_field_at(index=3, name=self.embed.fields[3].name, value=f"**{win}{money:,}** Credits.", inline=False)
            self.embed.add_field(name="Credits", value=f"You now have **{self.balance+money:,}** credits.")
            self.embed.set_footer()

        if color:
            self.embed.color = color

        self.embed.set_field_at(index=0, name=self.embed.fields[0].name, value=hint_message,
            inline=self.embed.fields[0].inline, ).set_field_at(index=1,  # player's hand
            name=self.embed.fields[1].name, value=player_cards, inline=self.embed.fields[1].inline, ).set_field_at(index=2,  # dealer's hand
            name=self.embed.fields[2].name, value=dealer_cards, inline=self.embed.fields[2].inline)
