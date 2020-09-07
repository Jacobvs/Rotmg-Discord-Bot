import asyncio
import datetime
import difflib
import logging
import random
import re
import time
from enum import Enum

import aiohttp
import discord
import humanfriendly as humanfriendly
import numpy as np
from discord.embeds import _EmptyEmbed
from discord.ext.commands import BadArgument, Converter

import sql
from cogs.Raiding.vc_select import VCSelect


class MemberLookupConverter(discord.ext.commands.MemberConverter):
    async def convert(self, ctx, mem, guild: discord.Guild = None) -> discord.Member:
        in_db = False
        if not ctx.guild:
            ctx.guild = guild

        if not mem.isdigit():
            try:
                data = await sql.get_user_from_ign(ctx.bot.pool, mem)
                if data:
                    in_db = True
                    member = await super().convert(ctx, str(data[0]))
                    return member
                else:
                    raise BadArgument(f"No members found with the name: {mem} and no results were found in the bot's database. "
                                      "Check your spelling and try again!")
            except discord.ext.commands.BadArgument:
                if isinstance(mem, str):
                    members = ctx.guild.members
                    if len(mem) > 5 and mem[-5] == '#':
                        # The 5 length is checking to see if #0000 is in the string,
                        # as a#0000 has a length of 6, the minimum for a potential
                        # discriminator lookup.
                        potential_discriminator = mem[-4:]

                        # do the actual lookup and return if found
                        # if it isn't found then we'll do a full name lookup below.
                        result = discord.utils.get(members, name=mem[:-5], discriminator=potential_discriminator)
                        if result is not None:
                            return result

                    def pred(m):
                        if m.nick:
                            if " | " in m.nick:
                                names = m.nick.split(" | ")
                                for n in names:
                                    if "".join([m.lower() for m in n if m.isalpha()]) == mem:
                                        return True
                            else:
                                if "".join([m.lower() for m in m.nick if m.isalpha()]) == mem:
                                    return True
                        return False

                    res = discord.utils.find(pred, members)
                    if res is not None:
                        return res

                try:
                    member = await super().convert(ctx, mem)  # Convert parameter to discord.member
                    return member
                except discord.ext.commands.BadArgument:
                    pass

                nicks = []
                mems = []
                for m in ctx.guild.members:
                    if m.nick:
                        nicks.append(m.nick.lower())
                        mems.append(m)

                res = difflib.get_close_matches(mem.lower(), nicks, n=1, cutoff=0.8)
                if res:
                    index = nicks.index(res[0])
                    return mems[index]

                desc = f"No members found with the name: {mem}. "
                desc += f"Found 1 result in the bot's database under the user: <@{data[0]}>. Verified in: [{data[6]}]" if in_db \
                    else "No results found in the bot's database. Check your spelling and try again!"
                raise BadArgument(desc)
        else:
            try:
                member = await super().convert(ctx, mem)  # Convert parameter to discord.member
                return member
            except discord.ext.commands.BadArgument:
                raise BadArgument(f"No members found with the name: {mem} and no results were found in the bot's database. "
                                  "Check your spelling and try again!")


class EmbedPaginator:

    def __init__(self, client, ctx, pages):
        self.client = client
        self.ctx = ctx
        self.pages = pages

    async def paginate(self):
        if self.pages:
            pagenum = 0
            embed: discord.Embed = self.pages[pagenum]
            if not isinstance(embed.title, _EmptyEmbed):
                if f" (Page {pagenum+1}/{len(self.pages)})" not in str(embed.title):
                    embed.title = embed.title + f" (Page {pagenum+1}/{len(self.pages)})"
            else:
                embed.title = f" (Page {pagenum+1}/{len(self.pages)})"
            msg = await self.ctx.send(embed=self.pages[pagenum])
            await msg.add_reaction("⏮️")
            await msg.add_reaction("⬅️")
            await msg.add_reaction("⏹️")
            await msg.add_reaction("➡️")
            await msg.add_reaction("⏭️")

            starttime = datetime.datetime.utcnow()
            timeleft = 300  # 5 minute timeout
            while True:
                def check(react, usr):
                    return not usr.bot and react.message.id == msg.id and usr.id == self.ctx.author.id and str(react.emoji) in \
                           ["⏮️", "⬅️", "⏹️", "➡️", "⏭️"]
                try:
                    reaction, user = await self.client.wait_for('reaction_add', timeout=timeleft, check=check)
                except asyncio.TimeoutError:
                    return await self.end_pagination(msg)

                if msg.guild:
                    await msg.remove_reaction(reaction.emoji, self.ctx.author)
                timeleft = 300 - (datetime.datetime.utcnow() - starttime).seconds
                if str(reaction.emoji) == "⬅️":
                    if pagenum == 0:
                        pagenum = len(self.pages)-1
                    else:
                        pagenum -= 1
                elif str(reaction.emoji) == "➡️":
                    if pagenum == len(self.pages)-1:
                        pagenum = 0
                    else:
                        pagenum += 1
                elif str(reaction.emoji) == "⏮️":
                    pagenum = 0
                elif str(reaction.emoji) == "⏭️":
                    pagenum = len(self.pages)-1
                elif str(reaction.emoji) == "⏹️":
                    return await self.end_pagination(msg)
                else:
                    continue

                embed: discord.Embed = self.pages[pagenum]
                if not isinstance(embed.title, _EmptyEmbed):
                    if f" (Page {pagenum + 1}/{len(self.pages)})" not in str(embed.title):
                        embed.title = embed.title + f" (Page {pagenum + 1}/{len(self.pages)})"
                else:
                    embed.title = f" (Page {pagenum + 1}/{len(self.pages)})"
                await msg.edit(embed=self.pages[pagenum])

    async def end_pagination(self, msg):
        try:
            if self.pages:
                await msg.edit(embed=self.pages[0])
            await msg.clear_reactions()
        except discord.NotFound:
            pass



class Card:
    """Class that represents a normal playing card."""

    suit_names = ['Clubs', 'Diamonds', 'Hearts', 'Spades']
    rank_names = [None, 'A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']


    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        self.suit_name = self.suit_names[suit]
        self.rank_name = self.rank_names[rank]
        self._card = (suit, rank)


    def __str__(self):
        return f'{self.rank_name} of {self.suit_name}'


    def __repr__(self):
        return f'{self.__class__.__name__}({self.suit}, {self.rank})'


    def __eq__(self, other):
        """Use the type tuple to make equality check."""

        return self._card == other._card


    def __lt__(self, other):
        """Use the type tuple to make the comparison.
        Sorts first by suit, then by rank.
        """
        return self._card < other._card


    @property
    def emoji(self):
        """Return a string of the card's rank and suit, in emoji form."""

        suit = Suits[self.suit_name.upper()].value
        if self.rank in (1, 11, 12, 13):
            rank = Alphabet[self.rank_name].value
        else:
            rank = Numbers[f'_{self.rank}'].value

        return rank + suit


class Deck:
    """Class that represents a full deck of cards, consisting of many
    Cards objects. Does not contain Jokers.
    """


    def __init__(self, cards=None):
        if cards is None:
            self.cards = [Card(suit, rank) for suit in range(4) for rank in range(1, 14)]
        else:
            self.cards = cards


    def __mul__(self, other):
        if isinstance(other, int):
            return self.__class__(cards=self.cards * other)
        else:
            raise ValueError('Invalid types for multiplication.')


    __rmul__ = __mul__


    def __len__(self):
        return len(self.cards)


    def __str__(self):
        return '\n'.join([str(card) for card in self.cards])


    def __iter__(self):
        return iter(self.cards)


    def __next__(self):
        return next(self.cards)


    def shuffle(self):
        """Shuffle the cards inplace."""

        np.random.shuffle(self.cards)


    def sort(self):
        """Sort the cards inplace."""

        self.cards.sort()


    def split(self, parts):
        """Split the deck in n parts."""

        cards_array = np.asarray(self.cards)
        split = np.array_split(cards_array, parts)
        decks = []
        for part in split:
            decks.append(self.__class__(cards=list(part)))

        return decks


    def add_card(self, card):
        """Add a card to the end of the deck."""

        self.cards.append(card)


    def remove_card(self, card):
        """Remove a given card form the deck."""

        self.cards.remove(card)


    def pop_card(self, *args):
        """Remove and return a card from the deck,
        the last one by default.
        """
        return self.cards.pop(*args)


    def give_cards(self, hand, amount):
        """Give the amount of cards from the deck to the player's hand."""

        for i in range(amount):
            hand.add_card(self.pop_card())


class Hand(Deck):
    """Class that represents the hand of a player.
    Inherits most from Deck class.
    """


    def __init__(self):
        self.cards = []


# Create an Enum with all the letters of the alphabet as emojis
Alphabet = Enum('Alphabet',
    {chr(char): chr(emoji) for char, emoji in zip(range(ord('A'), ord('Z') + 1), range(0x1F1E6, 0x1F200)  # :regional_indicator_#:
    )})


class Numbers(Enum):
    _0 = '\u0030\u20e3'  # :zero:
    _1 = '\u0031\u20e3'  # :one:
    _2 = '\u0032\u20e3'  # :two:
    _3 = '\u0033\u20e3'  # :three:
    _4 = '\u0034\u20e3'  # :four:
    _5 = '\u0035\u20e3'  # :five:
    _6 = '\u0036\u20e3'  # :six:
    _7 = '\u0037\u20e3'  # :seven:
    _8 = '\u0038\u20e3'  # :eight
    _9 = '\u0039\u20e3'  # :nine:
    _10 = '\U0001F51F'  # :keycap_ten:


class Controls(Enum):
    CANCEL = '\U0000274C'  # :x:


class Hangman(Enum):
    BLACK = '\U00002B1B'  # :black_large_square:
    DIZZY_FACE = '\U0001F635'  # :dizzy_face:
    SHIRT = '\U0001F455'  # :shirt:
    POINT_LEFT = '\U0001F448'  # :point_left:
    POINT_RIGHT = '\U0001F449'  # :point_right:
    JEANS = '\U0001F456'  # :jeans:
    SHOE = '\U0001F45E'  # :mans_shoe:
    BLANK = '\U000023F9'  # :stop_button:


class Connect4(Enum):
    BLACK = '\U000026AB'  # :black_circle:
    RED = '\U0001F534'  # :red_cirle:
    BLUE = '\U0001F535'  # :large_blue_circle:
    RED_WIN = '\U00002B55'  # :o:
    BLUE_WIN = '\U0001F518'  # :radio_button:


class Suits(Enum):
    SPADES = '\U00002660'  # :spades:
    CLUBS = '\U00002663'  # :clubs:
    HEARTS = '\U00002665'  # :hearts:
    DIAMONDS = '\U00002666'  # :diamonds:
    JOKER = '\U0001F0CF'  # :black_joker:


class HighLow(Enum):
    HIGH = '\U000023EB'  # :arrow_double_up:
    LOW = '\U000023EC'  # :arrow_double_down:


class TicTacToe(Enum):
    UL = '\U00002196'  # :arrow_upper_left:
    UM = '\U00002B06'  # :arrow_up:
    UR = '\U00002197'  # :arrow_upper_right:
    ML = '\U00002B05'  # :arrow_left:
    MM = '\U000023FA'  # :record_button:
    MR = '\U000027A1'  # :arrow_right:
    LL = '\U00002199'  # :arrow_lower_left:
    LM = '\U00002B07'  # :arrow_down:
    LR = '\U00002198'  # :arrow_lower_right:
    X = Alphabet.X.value  # :regional_indicator_x:
    O = '\U0001F17E'  # :o2:
    BLANK = '\U00002B1C'  # :white_large_square:


class RouletteGifs(Enum):
    _0 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004500/0_hw4ozi.gif"
    _1 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004506/1_d4hvgf.gif"
    _2 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004519/2_ffs0qi.gif"
    _3 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004524/3_ceclp8.gif"
    _4 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004478/4_rdaszs.gif"
    _5 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004482/5_sem3zb.gif"
    _6 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004503/6_xeiifa.gif"
    _7 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004536/7_v7avrx.gif"
    _8 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004480/8_uxpvdu.gif"
    _9 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004537/9_wptd9z.gif"
    _10 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004510/10_h85pj6.gif"
    _11 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004532/11_myjufk.gif"
    _12 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004538/12_ihb9cr.gif"
    _13 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004489/13_kfhkie.gif"
    _14 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004521/14_odqdlb.gif"
    _15 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004538/15_o9pfnj.gif"
    _16 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004500/16_rylldv.gif"
    _17 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004499/17_r9vre4.gif"
    _18 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004488/18_p67w69.gif"
    _19 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004510/19_hklqzo.gif"
    _20 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004512/20_chdzbq.gif"
    _21 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004518/21_p2uwou.gif"
    _22 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004479/22_q5cqyf.gif"
    _23 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004491/23_kpawtb.gif"
    _24 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004533/24_famfw9.gif"
    _25 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004531/25_sksh8g.gif"
    _26 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004521/26_mihjd4.gif"
    _27 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004489/27_bibte7.gif"
    _28 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004493/28_nipbll.gif"
    _29 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004515/29_gwskh5.gif"
    _30 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004528/30_fuhk2c.gif"
    _31 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004526/31_emmym4.gif"
    _32 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004535/32_salhf1.gif"
    _33 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004508/33_obghm6.gif"
    _34 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004481/34_pt4y0c.gif"
    _35 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004507/35_lzy82q.gif"
    _36 = "https://res.cloudinary.com/darkmattr/image/upload/v1589004498/36_eskj7v.gif"


def build_duration(**kwargs):
    """Converts a dict with the keys defined in `Duration` to a timedelta
    object. Here we assume a month is 30 days, and a year is 365 days.
    """
    weeks = kwargs.get('weeks', 0)
    days = 365 * kwargs.get('years', 0) + 30 * kwargs.get('months', 0) + kwargs.get('days')
    hours = kwargs.get('hours', 0)
    minutes = kwargs.get('minutes', 0)
    seconds = kwargs.get('seconds', 0)

    return datetime.timedelta(days=days, seconds=seconds, minutes=minutes, hours=hours, weeks=weeks, )


class Duration(Converter):
    """Convert duration strings into UTC datetime.datetime objects.
    Inspired by the https://github.com/python-discord/bot repository.
    """

    duration_parser = re.compile(r"((?P<years>\d+?) ?(years|year|Y|y) ?)?"
                                 r"((?P<months>\d+?) ?(months|month|M) ?)?"  # switched m to M
                                 r"((?P<weeks>\d+?) ?(weeks|week|W|w) ?)?"
                                 r"((?P<days>\d+?) ?(days|day|D|d) ?)?"
                                 r"((?P<hours>\d+?) ?(hours|hour|H|h) ?)?"
                                 r"((?P<minutes>\d+?) ?(minutes|minute|min|m) ?)?"  # switched M to m
                                 r"((?P<seconds>\d+?) ?(seconds|second|S|s))?")


    async def convert(self, ctx, duration: str) -> datetime.datetime:
        """
        Converts a `duration` string to a datetime object that's
        `duration` in the future.
        The converter supports the following symbols for each unit of time:
        - years: `Y`, `y`, `year`, `years`
        - months: `m`, `month`, `months`
        - weeks: `w`, `W`, `week`, `weeks`
        - days: `d`, `D`, `day`, `days`
        - hours: `H`, `h`, `hour`, `hours`
        - minutes: `m`, `minute`, `minutes`, `min`
        - seconds: `S`, `s`, `second`, `seconds`
        The units need to be provided in **descending** order of magnitude.
        """
        match = self.duration_parser.fullmatch(duration)
        if not match:
            raise BadArgument(f"`{duration}` is not a valid duration string.")

        duration_dict = {unit: int(amount) for unit, amount in match.groupdict(default=0).items()}
        delta = build_duration(**duration_dict)
        now = datetime.datetime.utcnow()

        return now + delta

def textProgressBar(iteration, total, prefix='```yml\nProgress:  ', percent_suffix="", suffix='\n```', decimals=1, length=100, fullisred=True, empty="<:gray:736515579103543336>"):
    """
    Call in a loop to create progress bar
    @params:
        iteration        - Required  : current iteration (Int)
        total            - Required  : total iterations (Int)
        prefix           - Optional  : prefix string (Str)
        percent_suffix   - Optional  : percent suffix (Str)
        suffix           - Optional  : suffix string (Str)
        decimals         - Optional  : positive number of decimals in percent complete (Int)
        length           - Optional  : character length of bar (Int)
        fill             - Optional  : bar fill character (Str)
        empty            - Optional  : bar empty character (Str)
    """
    iteration = total if iteration > total else iteration
    percent = 100 * (iteration / float(total))
    s_percent = ("{0:." + str(decimals) + "f}").format(percent)
    if fullisred:
        fill = "<:green:736390154549329950>" if percent <= 34 else "<:yellow:736390576932651049>" if percent <= 67 else "<:orange:736390576789782620>" \
            if percent <= .87 else "<:red:736390576978788363>"
    else:
        fill = "<:red:736390576978788363>" if percent <= 34 else "<:orange:736390576789782620>" if percent <= 67 else "<:yellow:736390576932651049>" \
            if percent <= .87 else "<:green:736390154549329950>"

    filledLength = int(length * iteration // total)
    bar = fill * filledLength + empty * (length - filledLength)
    res = f'{prefix} {bar} - {s_percent}% {percent_suffix} {suffix}' if percent_suffix != "" else f'\r{prefix}\n{bar}{suffix}'
    return res


async def check_pops(client, member, changed_amount, num, type=None, emoji=None, guild=None, ctx=None, hcchannel=None):
    if type:
        fname = "Keys" if type == "key" else "Event Keys" if type == "event" else "Vials" if type == "vial" else "Helm Runes" if \
            type == "helm" else "Shield Runes" if type == "shield" else "Sword Runes"
    else:
        fname=emoji

    guild = guild if guild else ctx.guild

    send_msg = False
    desc = f"{member.mention} has popped {num} {fname} for the server!"
    if num % 5 == 0:
        send_msg = True
    guild_db = client.guild_db.get(guild.id)
    if fname == 'Keys':
        fpopnum = guild_db[sql.gld_cols.numpopsfirst]
        if num >= fpopnum:
            role = guild_db[sql.gld_cols.firstpopperrole]
            if role and role not in member.roles:
                send_msg = True
                desc += f"\nThey have earned the {role.mention} role!"
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"ERROR: adding first key popper role to {member.display_name} failed!")
        spopnum = guild_db[sql.gld_cols.numpopssecond]
        if num >= spopnum:
            role = guild_db[sql.gld_cols.secondpopperrole]
            if role and role not in member.roles:
                send_msg = True
                desc += f"\nThey have earned the {role.mention} role!"
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"ERROR: adding second key popper role to {member.display_name} failed!")
        tpopnum = guild_db[sql.gld_cols.numpopsthird]
        if num >= tpopnum:
            role = guild_db[sql.gld_cols.thirdpopperrole]
            if role and role not in member.roles:
                send_msg = True
                desc += f"\nThey have earned the {role.mention} role!"
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"ERROR: adding third key popper role to {member.display_name} failed!")
    elif type == 'helm' or type == 'shield' or type == 'sword':
        d = await sql.get_log(client.pool, guild.id, member.id)
        nrunes = d[sql.log_cols.helmrunes] + d[sql.log_cols.swordrunes] + d[sql.log_cols.shieldrunes] if d else 0
        desc = f"{member.mention} has popped {nrunes} runes for the server! " \
               f"({d[sql.log_cols.helmrunes]} helm, {d[sql.log_cols.swordrunes]} sword, {d[sql.log_cols.shieldrunes]} shield)"
        frpopnum = guild_db[sql.gld_cols.numpopsfirstrune]
        if nrunes >= frpopnum:
            role = guild_db[sql.gld_cols.runepopper1role]
            if role and role not in member.roles:
                send_msg = True
                desc += f"\nThey have earned the {role.mention} role!"
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"ERROR: adding first rune popper role to {member.display_name} failed!")
        srpopnum = guild_db[sql.gld_cols.numpopssecondrune]
        if nrunes >= srpopnum:
            role = guild_db[sql.gld_cols.runepopper2role]
            if role and role not in member.roles:
                send_msg = True
                desc += f"\nThey have earned the {role.mention} role!"
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    print(f"ERROR: adding second rune popper role to {member.display_name} failed!")
    if send_msg:
        if not hcchannel:
            setup = VCSelect(client, ctx, log=True)
            data = await setup.start()
            if isinstance(data, tuple):
                (raidnum, inraiding, invet, inevents, raiderrole, rlrole, hcchannel, vcchannel, setup_msg) = data
            else:
                return
            try:
                await setup_msg.delete()
            except discord.NotFound:
                pass
        await hcchannel.send(desc)


async def image_upload(binary, sendable, is_rc=True):
    if is_rc:
        payload = {'file': binary, 'upload_preset': 'rotmg-rc-maps'}
    else:
        payload = {'file': binary, 'upload_preset': 'gh_issues'}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
            async with cs.request("POST", "https://api.cloudinary.com/v1_1/darkmattr/image/upload", data=payload) as r:
                if not r:
                    print(r)
                    logging.error("IMAGE UPLOAD ERROR")
                    return None
                else:
                    res = await r.json()
    except asyncio.TimeoutError:
        return await sendable.send("There was an issue uploading the image, please retry the command.", delete_after=10)
    return res


blacklisted_servers = ['uswest3', 'uswest', 'euwest', 'eueast', 'ussouth3', 'australia', 'asiaeast', 'asiasoutheast']
semi_blacklisted = ['uswest3', 'australia', 'asiasoutheast', 'asiaeast']
async def get_good_realms(client, max_pop, max_server_pop=70):
    blacklist = semi_blacklisted if max_pop > 10 else blacklisted_servers
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
            async with cs.request("GET", 'http://www.nebulanotifier.com/api/get/all', headers={'Authorization': client.nebula_token}) as r:
                if r.status == 200:
                    data = await r.json()
                    if data:
                        for r in list(data.keys()):
                            if r.lower() in blacklist:
                                del data[r]
                                continue
                            total = 0
                            for s in list(data[r].keys()):
                                total += data[r][s]['Population']
                                if data[r][s]['Population'] > max_pop:
                                    del data[r][s]

                            if total > max_server_pop:
                                del data[r]
                                continue

                        usdata = {}
                        eudata = {}
                        for r in data:
                            for s in data[r]:
                                stime = humanfriendly.format_timespan(int(time.time() - (data[r][s]['Timestamp']/1000)))
                                if 'US' == r[:2]:
                                    usdata[f"{r} {s}"] = {'Population': data[r][s]['Population'], "Events": data[r][s]['Events'], 'Curr_Event': data[r][s]['Event'],
                                                          'Time': stime}
                                else:
                                    eudata[f"{r} {s}"] = {'Population': data[r][s]['Population'], "Events": data[r][s]['Events'], 'Curr_Event': data[r][s]['Event'],
                                                          'Time': stime}

                        import json
                        d = sorted(usdata, key=lambda x: usdata[x]['Events'])
                        d = d[:4]
                        d2 = []
                        for s in d:
                            d2.append((s, usdata[s]['Population'], usdata[s]['Events'], usdata[s]['Curr_Event'], usdata[s]['Time']))
                        usdata = d2
                        d = sorted(eudata, key=lambda x: eudata[x]['Events'])
                        d = d[:4]
                        d2 = []
                        for s in d:
                            d2.append((s, eudata[s]['Population'], eudata[s]['Events'], eudata[s]['Curr_Event'], eudata[s]['Time']))
                        eudata = d2
                        return usdata, eudata

                return None
    except asyncio.TimeoutError:
        return None


async def get_event_servers(client, type):
    type = type.strip().lower()
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10)) as cs:
            async with cs.request("GET", 'http://www.nebulanotifier.com/api/get/all', headers={'Authorization': client.nebula_token}) as r:
                if r.status == 200:
                    data = await r.json()
                    if data:
                        for r in list(data.keys()):
                            for s in list(data[r].keys()):
                                if data[r][s]['Event'].strip().lower() != type:
                                    del data[r][s]

                        datad = {}
                        for r in data:
                            for s in data[r]:
                                datad[f"{r} {s}"] = {'Population': data[r][s]['Population'], "Events": data[r][s]['Events'], 'Curr_Event': data[r][s]['Event'],
                                                          'Timestamp': data[r][s]['Timestamp']/1000}

                        import json
                        d = sorted(datad, key=lambda x: datad[x]['Timestamp'], reverse=True)
                        d = d[:8]
                        d2 = []
                        for s in d:
                            d2.append((s, datad[s]['Population'], datad[s]['Events'], datad[s]['Curr_Event'],
                                       humanfriendly.format_timespan(int(time.time() - (datad[s]['Timestamp'])))))
                        data = d2
                        return data

                return None
    except asyncio.TimeoutError:
        return None


servers = {"US" : ("USWest2", "USWest", "USSouthWest", "USSouth3", "USSouth2", "USSouth", "USNorthWest", "USMidWest2", "USMidWest", "USEast3", "USEast2", "USEast"),
           "EU" : ("EUWest", "EUSouthWest", "EUSouth", "EUNorth2", "EUNorth")}

def get_server(is_us=True):
    res = random.choice(servers["EU"]) if is_us else random.choice(servers["US"])
    return res + random.choice([" Left", " Right"]) + " Bazaar"


oryx_images = [
    "https://i.imgur.com/mPp9HfN.gif",
    "https://i.imgur.com/c6Ck8KA.gif",
    "https://i.imgur.com/aAm0TfB.gif",
    "https://i.imgur.com/9HLRAcT.gif",
    "https://i.imgur.com/6Cwnzfi.gif",
    "https://i.imgur.com/tIj66nn.gif",
    "https://i.imgur.com/VqWnW9D.gif",
    "https://i.imgur.com/BivkiN0.gif",
    "https://i.imgur.com/ZQgIOzf.gif",
    "https://i.imgur.com/gJeniO7.gif",
    "https://i.imgur.com/hJTpbTZ.gif",
    "https://i.imgur.com/UmiD7hl.gif",
    "https://i.imgur.com/ImMoYzi.gif",
    "https://i.imgur.com/pYjQR9W.gif",
    "https://i.imgur.com/VqPKPUH.gif",
    "https://i.imgur.com/jhNLpiT.gif",
    "https://i.imgur.com/Qig5rY2.gif",
    "https://i.imgur.com/FFYAEws.gif",
    "https://i.imgur.com/Ct5XsHB.gif",
    "https://i.imgur.com/4VYcT6Z.gif"
]
def get_random_oryx():
    return random.choice(oryx_images)

# Queue Dungeons
# 0 : title
# 1 : dungeon emoji
# 2 : player cap - (total, nitro)
# 3 : required emojis (emoji, max)
# 4 : normal emojis
# 5 : dungeon color
# 6 : dungeon image
q_dungeons = {1: ("Oryx 3",
                  ("<a:O3:737899037973282856>", "https://i.imgur.com/Y37KxOF.gif"),
                  (80, 6),
                  (("<:WineCellarInc:708191799750950962>", 1),
                   ("<:swordrune:737672554482761739>", 2),
                   ("<:shieldrune:737672554642276423>", 2),
                   ("<:helmrune:737673058722250782>", 2),
                   ("<:puri:682205769973760001>", 4),
                   ("<:mseal:682205755754938409>", 2),
                   ("<:trickster:682214467483861023>", 2),
                   ("<:Bard:735022210657550367>", 1),
                   ("<:mystic:682205700918607969>", 2),
                   ("<:wizard:711307534685962281>", 6)),
                  ("<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                   "<:wizard:711307534685962281>", "<:Samurai:735022210682585098>"),
                 discord.Color.gold(),
                 "https://i.imgur.com/0qglf0F.gif"),
              2: ("Vet Oryx 3",
                  ("<a:O3:737899037973282856>", "https://i.imgur.com/Y37KxOF.gif"),
                  (46, 4),
                  (("<:WineCellarInc:708191799750950962>", 1),
                   ("<:swordrune:737672554482761739>", 1),
                   ("<:shieldrune:737672554642276423>", 1),
                   ("<:helmrune:737673058722250782>", 1),
                   ("<:puri:682205769973760001>", 4),
                   ("<:warrior:682204616997208084>", 4),
                   ("<:mseal:682205755754938409>", 3),
                   ("<:trickster:682214467483861023>", 2),
                   ("<:mystic:682205700918607969>", 2),
                   ("<:Bard:735022210657550367>", 2),
                   ("<:knight:682205672116584459>", 1),
                   ("<:Samurai:735022210682585098>", 1),
                   ('<:dps:751494941980753991>', 15)),
                  ("<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                   "<:wizard:711307534685962281>", "<:Samurai:735022210682585098>"),
                 discord.Color.gold(),
                 "https://i.imgur.com/0qglf0F.gif")
              }

def q_dungeon_info(num):
    info = q_dungeons.get(num)
    if num == 1:
        l = list(info[:6])
        l.append(get_random_oryx())
        return l
    return info if info else False


defaults = ["<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>"]
dungeons = {1: ("Oryx 3", ["<:oryx3:711426860051071067>", "<:WineCellarInc:708191799750950962>", "<:swordrune:737672554482761739>",
                           "<:shieldrune:737672554642276423>", "<:helmrune:737673058722250782>", "<:warrior:682204616997208084>",
                           "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                           "<:Bard:735022210657550367>"],
                ["<:puri:682205769973760001>", "<:mseal:682205755754938409>", "<:slow_icon:678792068965072906>", "<:mystic:682205700918607969>"],
                ["<:trickster:682214467483861023>"],
                discord.Color.gold(),
                "https://cdn.discordapp.com/attachments/561246036870430770/708192230468485150/oryx_3_w.png"),
            2: ("Cult", ["<:CultistHideout:585613559254482974>", "<:lhkey:682205801728835656>", "<:warrior:682204616997208084>",
                         "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                         "<:puri:682205769973760001>"],
                ["<:T2Orb:735022210728591420>", "<:knight:682205672116584459>"],
                ["<:planewalker:682212363889279091>"],
                discord.Color.red(), "https://i.imgur.com/nPkovWR.png"),
            3: ("MBC", ["<:MBC:727607969591853228>", "<:lhkey:682205801728835656>", "<:Samurai:735022210682585098>", "<:Bard:735022210657550367>",
                        "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>"],
                ["<:T1Orb:735022210510487583>", "<:brainofthegolem:682205737492938762>", "<:puri:682205769973760001>", "<:Ogmur:735022210460287038>",
                 "<:mseal:682205755754938409>"],
                [],
                discord.Color.from_rgb(166, 166, 166), "https://i.imgur.com/G8FArqL.png"),
            4: ("Void", ["<:void:682205817424183346>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>", "<:Samurai:735022210682585098>",
                         "<:Bard:735022210657550367>", "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                         "<:priest:682206578908069905>"],
                ["<:T1Orb:735022210510487583>", "<:brainofthegolem:682205737492938762>", "<:puri:682205769973760001>", "<:Ogmur:735022210460287038>",
                 "<:mseal:682205755754938409>"],
                [],
                discord.Color.from_rgb(19, 4, 79), "https://i.imgur.com/7JGSvMq.png"),
            5: ("Full-Skip Void", ["<:fskipvoid:682206558075224145>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>", "<:Ogmur:735022210460287038>",
                                   "<:Samurai:735022210682585098>", "<:Bard:735022210657550367>", "<:warrior:682204616997208084>", "<:knight:682205672116584459>",
                                   "<:paladin:682205688033968141>",
                                   "<:priest:682206578908069905>", "<:mseal:682205755754938409>"],
                ["<:T2Orb:735022210728591420>", "<:brainofthegolem:682205737492938762>", "<:puri:682205769973760001>"],
                [],
                discord.Color.from_rgb(19, 4, 79), "https://i.imgur.com/7JGSvMq.png"),
            6: ("Shatters", ["<:TheShatters:561744041532719115>", "<:ShattersKey:561744174152548374>", "<:warrior:682204616997208084>",
                            "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                             "<:mystic:682205700918607969>"],
                ["<:armorbreak:682206598156124212>", "<:orbofaether:682206626157035605>"],
                ["<:switch1:682206658461433986>", "<:switch2:682206673506533395>", "<:switch3:682206687083757569>"],
                discord.Color.from_rgb(78, 78, 78), "https://static.drips.pw/rotmg/wiki/Enemies/shtrs%20The%20Forgotten%20King.png"),
            7: ("Fungal Cavern", ["<:FungalCavern:609078085945655296>", "<:CavernKey:609078341529632778>",
                                  "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                                  "<:priest:682206578908069905>", "<:trickster:682214467483861023>", "<:mystic:682205700918607969>"],
                ["<:mseal:682205755754938409>", "<:QuiverofThunder:585616162176630784>", "<:armorbreak:682206598156124212>","<:slow_icon:678792068965072906>"],
                ["<:planewalker:682212363889279091>"],
                discord.Color.from_rgb(138, 194, 110), "https://i.imgur.com/K6rOQzR.png"),
            8: ("The Nest", ["<:Nest:585617025909653524>", "<:NestKey:585617056192266240>", "<:warrior:682204616997208084>",
                             "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                             "<:mystic:682205700918607969>"],
                ["<:puri:682205769973760001>", "<:QuiverofThunder:585616162176630784>", "<:slow_icon:678792068965072906>"],
                [],
                discord.Color.from_rgb(226, 117, 37), "https://i.imgur.com/hUWc3IV.png"),
            9: ("Full-Skip Nest", ["<:fskipNest:727606399621791934>", "<:NestKey:585617056192266240>", "<:warrior:682204616997208084>",
                             "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                             "<:mystic:682205700918607969>"],
                ["<:puri:682205769973760001>", "<:QuiverofThunder:585616162176630784>", "<:slow_icon:678792068965072906>"],
                [],
                discord.Color.from_rgb(226, 117, 37),
                "https://i.imgur.com/Qmsl0Pq.png"),
            10: ("Tomb", ["<:TomboftheAncientsPortal:561248700723363860>", "<:tombOfTheAncientsKey:561248916822163487>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                discord.Color.from_rgb(233, 197, 100), "https://static.drips.pw/rotmg/wiki/Enemies/Tomb%20Defender.png"),
            11: ("Ice Cave", ["<:IceCavePortal:561248701276880918>", "<:IceCaveKey:561248916620967949>"],
                 [],
                 [],
                discord.Color.from_rgb(82, 156, 247), "https://static.drips.pw/rotmg/wiki/Enemies/ic%20Esben%20the%20Unwilling.png"),
            12: ("Ocean Trench", ["<:OceanTrenchPortal:561248700601466891>", "<:oceanTrenchKey:561248917048655882>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(246, 52, 170), "https://static.drips.pw/rotmg/wiki/Enemies/Thessal%20the%20Mermaid%20Goddess.png"),
            13: ("Crawling Depths", ["<:TheCrawlingDepths:561248701591322644>", "<:theCrawlingDepthsKey:561248917052719104>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(71, 17, 10), "https://static.drips.pw/rotmg/wiki/Enemies/Son%20of%20Arachna.png"),
            14: ("Woodland Labyrinth", ["<:WoodlandLabyrinth:561248701440589824>", "<:woodlandLabyrinthKey:561248917115633667>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(31, 86, 9), "https://static.drips.pw/rotmg/wiki/Enemies/Murderous%20Megamoth.png"),
            15: ("Deadwater Docks", ["<:DeadwaterDocks:561248700324773909>", "<:deadwaterDocksKey:561248917052850176>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(184, 184, 184), "https://static.drips.pw/rotmg/wiki/Enemies/Jon%20Bilgewater%20the%20Pirate%20King.png"),
            16: ("Lair of Draconis", ["<:ConsolationofDraconisPortal:561248700672901120>", "<:lairOfDraconisKey:561248916931084320>"],
                 [],
                 [],
                 discord.Color.from_rgb(250, 231, 53), "https://i.imgur.com/beABgum.png"),
            17: ("Mountain Temple", ["<:mt:561248700769239076>", "<:mountainTempleKey:561248917027684367>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(46, 0, 1), "https://i.imgur.com/TIektVi.png"),
            18: ("Davy Jones Locker", ["<:DavyJonessLockerPortal:561248700295544883>", "<:davyJonesLockerKey:561248917086273536>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(58, 46, 88), "https://static.drips.pw/rotmg/wiki/Enemies/Davy%20Jones.png"),
            19: ("Parasite Chambers", ["<:Parasite:561248700727558144>", "<:parasiteChambersKey:561248917115633665>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(139, 33, 35), "https://i.imgur.com/zodPEFO.png"),
            20: ("Mad Lab", ["<:MadLabPortal:561248700899262469>", "<:madLabKey:561248917010776065>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(58, 43, 116), "https://static.drips.pw/rotmg/wiki/Enemies/Dr%20Terrible.png"),
            21: ("Machine", ["<:Machine:572596351204982784>", "<:machineKey:711442921211035701>"],
                 [],
                 [],
                 discord.Color.from_rgb(114, 219, 170), "https://i.imgur.com/G7Hbr58.png"),
            22: ("Cemetary", ["<:HauntedCemeteryPortal:561248700693741578>", "<:cemeteryKey:561248917052981278>"],
                 [],
                 [],
                 discord.Color.from_rgb(69, 129, 98), "https://static.drips.pw/rotmg/wiki/Enemies/Ghost%20of%20Skuld.png"),
            23: ("Cursed Library", ["<a:CursedLibraryPortal:576610298262454316>", "<:cursedLibraryKey:576610460690939914>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(50, 60, 101), "https://i.imgur.com/DfhWagx.png"),
            24: ("Toxic Sewers", ["<:ToxicSewersPortal:561248701213835265>", "<:toxicSewersKey:561248917145124874>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(90, 105, 93), "https://static.drips.pw/rotmg/wiki/Enemies/DS%20Gulpord%20the%20Slime%20God.png"),
            25: ("Puppet Master's Theatre", ["<:PuppetTheatrePortal:561248700408791051>", "<:theatreKey:561248917065433119>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(128, 3, 8), "https://static.drips.pw/rotmg/wiki/Enemies/The%20Puppet%20Master.png"),
            26: ("Manor", ["<:ManoroftheImmortalsPortal:561248700337225759>", "<:manorKey:561248917120090142>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(129, 95, 138), "https://static.drips.pw/rotmg/wiki/Enemies/Lord%20Ruthven.png"),
            27: ("Abyss", ["<:AbyssofDemonsPortal:561248700643409931>", "<:abyssOfDemonsKey:561248916624900097>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(175, 13, 28), "https://static.drips.pw/rotmg/wiki/Enemies/Archdemon%20Malphas.png"),
            28: ("Undead Lair", ["<:UndeadLairPortal:561248700601729036>", "<:undeadLairKey:561248917090729999>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(115, 115, 115), "https://static.drips.pw/rotmg/wiki/Enemies/Septavius%20the%20Ghost%20God.png"),
            29: ("Treasure Cave", ["<:TreasureCavePortal:561248701809557511>", "<:caveOfAThousandTreasuresKey:561248916968964129>"],
                 [],
                 [],
                 discord.Color.gold(), "https://static.drips.pw/rotmg/wiki/Enemies/Golden%20Oryx%20Effigy.png"),
            30: ("Candyland", ["<:CandylandPortal:561248700916301825>", "<:candylandKey:561248916989935656>"],
                 [],
                 [],
                 discord.Color.from_rgb(250, 73, 79), "https://static.drips.pw/rotmg/wiki/Enemies/Gigacorn.png"),
            31: ("Sprite World", ["<:GlowingPortal:561249801501540363>", "<:spriteWorldKey:561249834292477967>"],
                 [],
                 [],
                 discord.Color.from_rgb(255, 255, 255), "https://static.drips.pw/rotmg/wiki/Enemies/Limon%20the%20Sprite%20God.png"),
            32: ("Magic Woods", ["<:MagicWoodPortal:561248700870033408>", "<:magicWoodsKey:561248916805386270>"],
                 [],
                 [],
                 discord.Color.from_rgb(164, 117, 56), "https://i.imgur.com/jVimXOv.png"),
            33: ("Hive", ["<:Hive:711430596714430535>", "<:hiveKey:711443611425832981>"],
                 [],
                 [],
                 discord.Color.from_rgb(146, 122, 28), "https://static.drips.pw/rotmg/wiki/Enemies/TH%20Queen%20Bee.png"),
            34: ("Forbidden Jungle", ["<:ForbiddenJungle:711430596571955363>", "<:forbiddenJungleKey:711443611794800670>"],
                 [],
                 [],
                 discord.Color.from_rgb(138, 195, 13), "https://static.drips.pw/rotmg/wiki/Enemies/Mixcoatl%20the%20Masked%20God.png"),
            35: ("Snake Pit", ["<:SnakePitPortal:561248700291088386>", "<:snakePitKey:561248916734083075>"],
                 [],
                 [],
                 discord.Color.from_rgb(39, 174, 74), "https://static.drips.pw/rotmg/wiki/Enemies/Stheno%20the%20Snake%20Queen.png"),
            36: ("Spider Den", ["<:SpiderDen:711430596567760957>", "<:spiderDenKey:711443611371175978>"],
                 [],
                 [],
                 discord.Color.from_rgb(34, 106, 31), "https://static.drips.pw/rotmg/wiki/Enemies/Arachna%20the%20Spider%20Queen.png"),
            37: ("Forest Maze", ["<:ForestMaze:711430596752179241>", "<:forestMazeKey:711443611568439367>"],
                 [],
                 [],
                 discord.Color.from_rgb(77, 114, 16), "https://static.drips.pw/rotmg/wiki/Enemies/Mama%20Mothra.png"),
            38: ("Pirate Cave", ["<:PirateCavePortal:574080648000569353>", "<:pirateCaveKey:711443611429896245>"],
                 [],
                 [],
                 discord.Color.from_rgb(107, 64, 32), "https://static.drips.pw/rotmg/wiki/Enemies/Dreadstump%20the%20Pirate%20King.png"),
            39: ("Beachzone", ["<:BeachzonePortal:711430895051079740>", "<:beachzoneKey:711444566103949392>"],
                 [],
                 [],
                 discord.Color.from_rgb(239, 159, 59), "https://static.drips.pw/rotmg/wiki/Enemies/Masked%20Party%20God.png"),
            40: ("Belladonnas Garden", ["<:BelladonnasGardenPortal:561248700693741569>", "<:BelladonnasGardenKey:561248916830552067>"],
                 [],
                 [],
                 discord.Color.from_rgb(214, 17, 110), "https://i.imgur.com/d7xzYLG.png"),
            41: ("Ice Tomb", ["<:IceTombPortal:561248700270116869>", "<:iceTombKey:561248917082079272>"],
                 [],
                 [],
                 discord.Color.from_rgb(209, 255, 247), "https://static.drips.pw/rotmg/wiki/Enemies/Ice%20Tomb%20Defender.png"),
            42: ("Battle Nexus", ["<:BattleNexusPortal:561248700588883979>", "<:battleOfTheNexusKey:561248916570505219>"],
                 [],
                 [],
                 discord.Color.from_rgb(239, 216, 103), "https://static.drips.pw/rotmg/wiki/Enemies/Oryx%20the%20Mad%20God%20Deux.png"),
            43: ("Red Aliens", ["<:AlienRed:711431346698059858>", "<:alienRedKey:711445699392438302>"],
                 [],
                 [],
                 discord.Color.from_rgb(252, 94, 69), "https://i.imgur.com/BLPokRW.png"),
            44: ("Blue Aliens", ["<:AlienBlue:711431346740002878>", "<:alienBlueKey:711445699241312259>"],
                 [],
                 [],
                 discord.Color.from_rgb(96, 192, 238), "https://i.imgur.com/TQOdFo6.png"),
            45: ("Green Aliens", ["<:AlienGreen:711431347029409853>", "<:alienGreenKey:711445699308290068>"],
                 [],
                 [],
                 discord.Color.from_rgb(197, 251, 83), "https://i.imgur.com/BEToOal.png"),
            46: ("Yellow Aliens", ["<:AlienYellow:711431347108839424>", "<:alienYellowKey:711445699195043850>"],
                 [],
                 [],
                 discord.Color.from_rgb(255, 254, 131), "https://i.imgur.com/C3kJ0x8.png"),
            47: ("Shaitan's Lair", ["<:LairofShaitanPortal:561248700828090388>", "<:shaitansKey:561248917191131152>"],
                 [],
                 [],
                 discord.Color.from_rgb(252, 106, 33), "https://i.imgur.com/azzD6jD.png"),
            48: ("Puppet Master's Encore", ["<:PuppetEncorePortal:561248700723101696>", "<:puppetMastersEncoreKey:561248917082079252>"],
                 [],
                 [],
                 discord.Color.from_rgb(103, 21, 23), "https://static.drips.pw/rotmg/wiki/Enemies/Puppet%20Master%20v2.png"),
            49: ("Cnidarian Reef", ["<:Reef:561250455284350998>", "<:reefKey:561251664388947968>"],
                 [],
                 [],
                 discord.Color.from_rgb(254, 188, 126), "https://i.imgur.com/BF2DclQ.png"),
            50: ("Secluded Thicket", ["<:thicket:561248701402578944>", "<:thicketKey:561248917208039434>"],
                 [],
                 [],
                 discord.Color.from_rgb(139, 195, 29), "https://i.imgur.com/xFWvgyV.png"),
            51: ("Heroic UDL", ["<:HUDL:711479365602508820>", "<:hudlKey:711444346334871643>"],
                 [],
                 [],
                 discord.Color.from_rgb(254, 196, 54), "https://i.imgur.com/WmL1qda.png"),
            52: ("Heroic Abyss", ["<:HAbyss:711431861678637129>", "<:habbyKey:711444346263830559>"],
                 [],
                 [],
                 discord.Color.from_rgb(254, 196, 54), "https://i.imgur.com/LCALe5V.png"),
            53: ("Janus", ["<:Janus:727609287148306552>", '<:WineCellarInc:708191799750950962>', "<:trickster:682214467483861023>",
                           "<:ninja_3:585616162151202817>", "<:warrior:682204616997208084>", "<:knight:682205672116584459>",
                           "<:paladin:682205688033968141>", "<:priest:682206578908069905>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(120, 49, 189), "https://i.imgur.com/RfObrpY.png"),
            54: ("Oryx 2", ["<:O2:727610126592376873>", '<:WineCellarInc:708191799750950962>', "<:trickster:682214467483861023>",
                           "<:ninja_3:585616162151202817>", "<:warrior:682204616997208084>", "<:knight:682205672116584459>",
                           "<:paladin:682205688033968141>", "<:priest:682206578908069905>"],
                 [],
                 ["<:planewalker:682212363889279091>"],
                 discord.Color.from_rgb(0, 0, 0), "https://static.drips.pw/rotmg/wiki/Enemies/Oryx%20the%20Mad%20God%202.png"),
            55: ("Keyper Clearing", ["<:whitebag:682208350481547267>", '<:WineCellarInc:708191799750950962>',
                           "<:trickster:682214467483861023>", "<:ninja_3:585616162151202817>", "<:warrior:682204616997208084>",
                           "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>"],
                 [],
                 ["<:planewalker:682212363889279091>"], discord.Color.from_rgb(20, 125, 236), "https://i.imgur.com/ldJqTmK.png")
            }

def dungeon_info(num: int = None):
    if not num:
        return dungeons
    else:
        res = dungeons.get(num)
        if not res:
            return dungeons
        if len(res[1]) == 2:
            return tuple((res[0], res[1] + defaults, res[2], res[3], res[4], res[5]))
        return res


def rand_dungon_keys():
    keys = ["<:defaultdungeon:682212333182910503>", '<:WineCellarInc:708191799750950962>', '<:lhkey:682205801728835656>',
            '<:ShattersKey:561744174152548374>',
            '<:CavernKey:609078341529632778>', '<:NestKey:585617056192266240>', '<:tombOfTheAncientsKey:561248916822163487>',
            '<:IiceCaveKey:561248916620967949>', '<:oceanTrenchKey:561248917048655882>', '<:theCrawlingDepthsKey:561248917052719104>',
            '<:woodlandLabyrinthKey:561248917115633667>', '<:deadwaterDocksKey:561248917052850176>',
            '<:lairOfDraconisKey:561248916931084320>', '<:mountainTempleKey:561248917027684367>',
            '<:davyJonesLockerKey:561248917086273536>', '<:parasiteChambersKey:561248917115633665>', '<:madLabKey:561248917010776065>',
            '<:machineKey:711442921211035701>', '<:cemeteryKey:561248917052981278>', '<:cursedLibraryKey:576610460690939914>',
            '<:toxicSewersKey:561248917145124874>', '<:theatreKey:561248917065433119>', '<:manorKey:561248917120090142>',
            '<:abyssOfDemonsKey:561248916624900097>', '<:undeadLairKey:561248917090729999>',
            '<:caveOfAThousandTreasuresKey:561248916968964129>', '<:candylandKey:561248916989935656>',
            '<:spriteWorldKey:561249834292477967>', '<:magicWoodsKey:561248916805386270>', '<:hiveKey:711443611425832981>',
            '<:forbiddenJungleKey:711443611794800670>', '<:snakePitKey:561248916734083075>', '<:spiderDenKey:711443611371175978>',
            '<:forestMazeKey:711443611568439367>', '<:pirateCaveKey:711443611429896245>', '<:beachzoneKey:711444566103949392>',
            '<:BelladonnasGardenKey:561248916830552067>', '<:iceTombKey:561248917082079272>', '<:battleOfTheNexusKey:561248916570505219>',
            '<:alienRedKey:711445699392438302>', '<:alienBlueKey:711445699241312259>', '<:alienGreenKey:711445699308290068>',
            '<:alienYellowKey:711445699195043850>', '<:shaitansKey:561248917191131152>', '<:puppetMastersEncoreKey:561248917082079252>',
            '<:reefKey:561251664388947968>', '<:thicketKey:561248917208039434>', '<:hudlKey:711444346334871643>',
            '<:habbyKey:711444346263830559>']
    return keys


def darkjoke():
    jokes = [('Killing black people is like saying the n word',
              'Black people do it all the time but get angry when a white person joins in'),
             ('How do you get a school shooting to happen at a Black school?', 'Call the cops'),
             ("When someone says rape jokes aren’t funny, I don't care","It's not like I asked for their consent anyway"),
             ('What did the jew say when he was recaptured by the nazis?', "Auschwitz, here we go again"),
             ("Terrorism makes no sense. Commit suicide and might get 72 virgins?", "Become a Catholic priest and get them now"), (
             "Whenever I see a woman driving a bus I smile and think about how far we as a society have come",
             "And then I wait for the next bus"),
             ("People are like teeth", "White ones are better, most are yellow, and black ones don’t work"),
             ("What’s the difference between Me and Cancer", "My dad didn’t beat cancer"), (
             "I don't understand why Obama had to make speeches behind bullet-proof glass",
             "I mean, I know he's black and all, but I highly doubt he'll shoot anyone"), (
             "What's the difference between science and religion?",
             "One builds planes and skyscrapers, and the other brings them together"),
             ("Does my Thai girlfriend have a penis?", "Something inside me says yes"),
             ("Congrats to Mac miller", "More than one year sober"),
             ("How do you start a rave?", "Throw a flashbang into the epilepsy ward"),
             ("I wish my lawn was a 16 year old girl", "Because then it could just cut itself"),
             ("What do people and sharks have in common?", "All the great ones are white"),
             ("Why are there no black priests?", "We called them 'father' and they suddenly disappeared"),
             ("What's a word that starts with an 'N' and ends with an 'R' that you don't want to call a black person?", "Neighbor"),
             ("What's the good thing about FaceApp?", "Kids with cancer can see themselves older"),
             ("What's 6 miles long and has an IQ of 10?", "A parade in pakistan"),
             ("What’s faster than a black man with your tv?", "His brother with your Xbox"),
             ("I don’t believe in evolution", "If it were real, black people would be bulletproof by now"), (
             "My first football game was a lot like how I lost my virginity", "I was bloody and sore at the end, but at least my dad came"),
             ("I love my girlfriend <3", "But she can be 4 too"),
             ("Why are black people's bones so fragile?", "Because their dads never came back with the milk"),
             ("Why do black people get hit by cars more in the winter?", "Because they’re easier to see"),
             ("What do you call a fat woman with a rape whistle?", "Optimistic"),
             ("I beat my wife and got arrested for destruction of property"),
             ("What’s the worst thing about vegetables?", "You can’t eat the wheelchair."),
             ("After being strangled, which organ in the female body remains warm after death?", "My cock."),
             ("What activity do 9 out of 10 people like to take part in?", "Gang rape."),
             ("What's the difference between Jews and money?", "I'd care if I lost 6 million dollars."),
             ("Whats the difference between Isaac Newton and the baby I just stabbed to death?", "Isaac Newton died a virgin."),
             ("Whats the best rated hotel?", "Auschwitz, 6 million stars"),
             ("I like my women like I like my wine", "Twelve years old and in my basement"), ("What does the w in muslim stand for?"
                                                                                              "women's rights"),
             ("Why are all runners in the Olympics black?", "Because when they hear the gun, they run faster"),
             ("What's the difference between a black man and a bench?", "One can support a family"),
             ("Why should you be scared of white people in prison?", "Because you know they're actually in there for a reason"),
             ("Why don't black people get presents on christmas?", "Because jails haven't needed chimneys since the holocaust"),
             ("Women aren't objects", "Because objects actually have value"),
             ("A group of blacks and whites are playing basketball in prison. Who wins?", "The blacks win because of home advantage"),
             ("Why are Americans so stupid?", "Because the ones that go to school get shot"),
             ("What can children cure?", "Erectile Disfunction"),
             ("What’s red, 4 inches long, and makes my girlfriend cry when I feed it to her?", "Her miscarriage"),
             ("What is the difference between Santa and a jew?", "Santa goes down the chimney"),
             ("What's the difference between a Jew and a bullet?", "A bullet leaves the chamber")]
    return random.choice(jokes)

def get_roast():
    roasts = [
        "at least my mom pretends to love me",
        "Don't play hard to get when you are hard to want",
        "Don't you worry your pretty little head about it. The operative word being little. Not pretty.",
        "God wasted a good asshole when he put teeth in your mouth",
        "Goddamn did your parents dodge a bullet when they abandoned you.",
        "I can't even call you ugly, because nature has already beaten me to it.",
        "I don't have the time, or the crayons to explain this to you.",
        "I hope you win the lottery and lose your ticket.",
        "I once smelled a dog fart that had more personality than you.",
        "I want to call you a douche, but that would be unfair and unrealistic. Douches are often found near vaginas.",
        "I wonder if you'd be able to speak more clearly if your parents were second cousins instead of first.",
        "I would call you a cunt, but you lack the warmth or the depth.",
        "I would rather be friends with Ajit Pai than you.",
        "I'd love to stay and chat but I'd rather have type-2 diabetes",
        "I'm just surprised you haven't yet retired from being a butt pirate.",
        "I'm not mad. I'm just... disappointed.",
        "I've never met someone who's at once so thoughtless, selfish, and uncaring of other people's interests, "
        "while also having such lame and boring interests of his own. You don't have friends, because you shouldn't.",
        "I’m betting your keyboard is crusty from all that Cheeto-dust finger typing, you goddamn neckbeard. ",
        "If 'unenthusiastic handjob' had a face, your profile picture would be it.",
        "If there was a single intelligent thought in your head it would have died from loneliness.",
        "If you were a potato you'd be a stupid potato.",
        "If you were an inanimate object, you'd be a participation trophy.",
        "If you where any stupider we'd have to water you",
        "If you're dad wasn't so much of a pussy, he'd have come out of the closet before he had you.",
        "Jesus Christ it looks like your face was on fire and someone tried to put it out with an ice pick",
        "Mr. Rogers would be disappointed in you.",
        "Next time, don't take a laxative before you type because you just took a steaming stinking dump right on the page. "
        "Now wipe that shit up and don't fuck it up like your life.",
        "Not even your dog loves you. He's just faking it.",
        "Once upon a time, Santa Claus was asked what he thought of your mom, your sister and your grandma, "
        "and thus his catchphrase was born.",
        "People don't even pity you.",
        "People like you are the reason God doesn't talk to us anymore",
        "Take my lowest priority and put yourself beneath it.",
        "The IQ test only goes down to zero but you make a really compelling case for negative numbers",
        "The only thing you're fucking is natural selection",
        "There are two ugly people in this chat, and you're both of them.",
        "There will never be enough middle fingers in this world for you",
        "They don't make a short enough bus in the world for a person like you.",
        "Those aren't acne scars, those are marks from the hanger.",
        "Twelve must be difficult for you. I don’t mean BEING twelve, I mean that being your IQ.",
        "We all dislike you, but not quite enough that we bother to think about you.",
        "Were you born a cunt, or is it something you have to commit yourself to every morning?",
        "When you die, people will struggle to think of nice things to say about you.",
        "Why don’t you crawl back to whatever micro-organism cesspool you came from, "
        "and try not to breath any of our oxygen on the way there",
        "You are a pizza burn on the roof of the world's mouth.",
        "You are dumber than a block of wood and not nearly as useful",
        "You are like the end piece of bread in a loaf, everyone touches you but no one wants you",
        "You have a face made for radio",
        "You have more dick in your personality than you do in your pants",
        "You have the face of a bulldog licking piss off a stinging nettle.",
        "You know they say 90% of dust is dead human skin? That's what you are to me.",
        "You look like your father would be disappointed in you. If he stayed.",
        "You losing your virginity is like a summer squash growing in the middle of winter. Never happening.",
        "You may think people like being around you- but remember this: there is a difference between being liked and being tolerated.",
        "You might want to get a colonoscopy for all that butthurt",
        "You should put a condom on your head, because if you're going to act like a dick you better dress like one too.",
        "You're an example of why animals eat their young.",
        "You're impossible to underestimate",
        "You're kinda like Rapunzel except instead of letting down your hair you let down everyone in your life",
        "You're like a penny on the floor of a public restroom - filthy, untouchable and practically worthless.",
        "You're like a square blade, all edge and no point.",
        "You're not pretty enough to be this dumb",
        "You're objectively unattractive.",
        "You're so dense, light bends around you.",
        "You're so salty you would sink in the Dead Sea",
        "You're so stupid you couldn't pour piss out of a boot if the directions were written on the heel",
        "You're such a pussy that fucking you wouldn't be gay.",
        "Your birth certificate is an apology letter from the abortion clinic.",
        "Your memes are trash.",
        "Your mother may have told you that you could be anything you wanted, but a douchebag wasn't what she meant."]
    return random.choice(roasts)


async def only_role_higher_channel(guild, channel, role):
    roles = guild.roles