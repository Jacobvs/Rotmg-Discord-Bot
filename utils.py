import asyncio
import datetime
import logging
import re
from enum import Enum

import aiohttp
import discord
import numpy as np
from discord.ext.commands import BadArgument, Converter

import sql


class MemberLookupConverter(discord.ext.commands.MemberConverter):
    async def convert(self, ctx, mem) -> discord.Member:
        in_db = False
        try:
            member = await super().convert(ctx, mem)  # Convert parameter to discord.member
        except discord.ext.commands.BadArgument:
            if isinstance(mem, str):
                try:
                    data = await sql.get_user_from_ign(ctx.bot.pool, mem)
                    if data:
                        in_db = True
                        member = await super().convert(ctx, str(data[0]))
                    else:
                        raise BadArgument(f"No members found with the name: {mem} and no results were found in the bot's database. "
                                          "Check your spelling and try again!")
                except discord.ext.commands.BadArgument:
                    desc = f"No members found with the name: {mem}. "
                    desc += f"Found 1 result in the bot's database under the user: <@{data[0]}>. Verified in: [{data[6]}]" if in_db \
                        else "No results found in the bot's database. Check your spelling and try again!"
                    raise BadArgument(desc)
            else:
                raise BadArgument(f"No members found with the name: `{mem}`")
        return member



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


    async def convert(self, ctx, duration: str) -> datetime:
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


async def image_upload(binary, ctx):
    payload = {'file': binary, 'upload_preset': 'rotmg-rc-maps'}
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
        return await ctx.send("There was an issue uploading the image, please retry the command.", delete_after=10)
    return res


def dungeon_info(num: int = None):
    defaults = ["<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>"]
    dungeons = {1: ("Oryx 3", ["<:oryx3:711426860051071067>", "<:WineCellarInc:708191799750950962>", "<:SwordRune:708191783405879378>",
                               "<:ShieldRune:708191783674314814>", "<:HelmRune:708191783825178674>", "<:warrior:682204616997208084>",
                               "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                               "<:mseal:682205755754938409>", "<:puri:682205769973760001>", "<:armorbreak:682206598156124212>"],
                    "https://cdn.discordapp.com/attachments/561246036870430770/708192230468485150/oryx_3_w.png"),
                2: ("Cult", ["<:CultistHideout:585613559254482974>", "<:lhkey:682205801728835656>", "<:warrior:682204616997208084>",
                             "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                             "<:puri:682205769973760001>", "<:planewalker:682212363889279091>"], "https://i.imgur.com/nPkovWR.png"),
                3: ("Void", ["<:void:682205817424183346>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                             "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                             "<:priest:682206578908069905>", "<:mseal:682205755754938409>", "<:puri:682205769973760001>",
                             "<:planewalker:682212363889279091>"], "https://i.imgur.com/7JGSvMq.png"),
                4: ("Full-Skip Void", ["<:fskipvoid:682206558075224145>", "<:lhkey:682205801728835656>", "<:vial:682205784524062730>",
                                       "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                                       "<:priest:682206578908069905>", "<:mystic:682205700918607969>", "<:mseal:682205755754938409>",
                                       "<:puri:682205769973760001>", "<:brainofthegolem:682205737492938762>"],
                    "https://i.imgur.com/7JGSvMq.png"),
                5: ("Shatters", ["<:TheShatters:561744041532719115>", "<:ShattersKey:561744174152548374>", "<:warrior:682204616997208084>",
                                "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                                 "<:mystic:682205700918607969>", "<:armorbreak:682206598156124212>", "<:orbofaether:682206626157035605>",
                                 "<:switch1:682206658461433986>", "<:switch2:682206673506533395>", "<:switch3:682206687083757569>"],
                    "https://static.drips.pw/rotmg/wiki/Enemies/shtrs%20The%20Forgotten%20King.png"),
                6: ("Fungal Cavern", ["<:FungalCavern:609078085945655296>", "<:CavernKey:609078341529632778>",
                                      "<:warrior:682204616997208084>", "<:knight:682205672116584459>", "<:paladin:682205688033968141>",
                                      "<:priest:682206578908069905>", "<:trickster:682214467483861023>", "<:mystic:682205700918607969>",
                                      "<:planewalker:682212363889279091>", "<:mseal:682205755754938409>",
                                      "<:QuiverofThunder:585616162176630784>", "<:armorbreak:682206598156124212>",
                                      "<:slow_icon:678792068965072906>"], "https://i.imgur.com/K6rOQzR.png"),
                7: ("The Nest", ["<:Nest:585617025909653524>", "<:NestKey:585617056192266240>", "<:warrior:682204616997208084>",
                                 "<:knight:682205672116584459>", "<:paladin:682205688033968141>", "<:priest:682206578908069905>",
                                 "<:mystic:682205700918607969>", "<:puri:682205769973760001>", "<:QuiverofThunder:585616162176630784>",
                                 "<:slow_icon:678792068965072906>"], "https://i.imgur.com/hUWc3IV.png"),
                8: ("Tomb", ["<:TomboftheAncientsPortal:561248700723363860>", "<:tombOfTheAncientsKey:561248916822163487>"],
                    "https://static.drips.pw/rotmg/wiki/Enemies/Tomb%20Defender.png"),
                9: ("Ice Cave", ["<:IceCavePortal:561248701276880918>", "<:IiceCaveKey:561248916620967949>"],
                    "https://static.drips.pw/rotmg/wiki/Enemies/ic%20Esben%20the%20Unwilling.png"),
                10: ("Ocean Trench", ["<:OceanTrenchPortal:561248700601466891>", "<:oceanTrenchKey:561248917048655882>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Thessal%20the%20Mermaid%20Goddess.png"),
                11: ("Crawling Depths", ["<:TheCrawlingDepths:561248701591322644>", "<:theCrawlingDepthsKey:561248917052719104>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Son%20of%20Arachna.png"),
                12: ("Woodland Labyrinth", ["<:WoodlandLabyrinth:561248701440589824>", "<:woodlandLabyrinthKey:561248917115633667>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Murderous%20Megamoth.png"),
                13: ("Deadwater Docks", ["<:DeadwaterDocks:561248700324773909>", "<:deadwaterDocksKey:561248917052850176>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Jon%20Bilgewater%20the%20Pirate%20King.png"),
                14: ("Lair of Draconis", ["<:ConsolationofDraconisPortal:561248700672901120>", "<:lairOfDraconisKey:561248916931084320>"],
                     "https://i.imgur.com/beABgum.png"),
                15: ("Mountain Temple", ["<:mt:561248700769239076>", "<:mountainTempleKey:561248917027684367>"],
                     "https://i.imgur.com/TIektVi.png"),
                16: ("Davy Jones Locker", ["<:DavyJonessLockerPortal:561248700295544883>", "<:davyJonesLockerKey:561248917086273536>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Davy%20Jones.png"),
                17: ("Parasite Chambers", ["<:Parasite:561248700727558144>", "<:parasiteChambersKey:561248917115633665>"],
                     "https://i.imgur.com/zodPEFO.png"),
                18: ("Mad Lab", ["<:MadLabPortal:561248700899262469>", "<:madLabKey:561248917010776065>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Dr%20Terrible.png"),
                19: ("Machine", ["<:Machine:572596351204982784>", "<:machineKey:711442921211035701>"],
                     "https://i.imgur.com/G7Hbr58.png"),
                20: ("Cemetary", ["<:HauntedCemeteryPortal:561248700693741578>", "<:cemeteryKey:561248917052981278>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Ghost%20of%20Skuld.png"),
                21: ("Cursed Library", ["<a:CursedLibraryPortal:576610298262454316>", "<:cursedLibraryKey:576610460690939914>"],
                     "https://i.imgur.com/DfhWagx.png"),
                22: ("Toxic Sewers", ["<:ToxicSewersPortal:561248701213835265>", "<:toxicSewersKey:561248917145124874>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/DS%20Gulpord%20the%20Slime%20God.png"),
                23: ("Puppet Master's Theatre", ["<:PuppetTheatrePortal:561248700408791051>", "<:theatreKey:561248917065433119>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/The%20Puppet%20Master.png"),
                24: ("Manor", ["<:ManoroftheImmortalsPortal:561248700337225759>", "<:manorKey:561248917120090142>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Lord%20Ruthven.png"),
                25: ("Abyss", ["<:AbyssofDemonsPortal:561248700643409931>", "<:abyssOfDemonsKey:561248916624900097>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Archdemon%20Malphas.png"),
                26: ("Undead Lair", ["<:UndeadLairPortal:561248700601729036>", "<:undeadLairKey:561248917090729999>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Septavius%20the%20Ghost%20God.png"),
                27: ("Treasure Cave", ["<:TreasureCavePortal:561248701809557511>", "<:caveOfAThousandTreasuresKey:561248916968964129>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Golden%20Oryx%20Effigy.png"),
                28: ("Candyland", ["<:CandylandPortal:561248700916301825>", "<:candylandKey:561248916989935656>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Gigacorn.png"),
                29: ("Sprite World", ["<:GlowingPortal:561249801501540363>", "<:spriteWorldKey:561249834292477967>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Limon%20the%20Sprite%20God.png"),
                30: ("Magic Woods", ["<:MagicWoodPortal:561248700870033408>", "<:magicWoodsKey:561248916805386270>"],
                     "https://i.imgur.com/jVimXOv.png"),
                31: ("Hive", ["<:Hive:711430596714430535>", "<:hiveKey:711443611425832981>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/TH%20Queen%20Bee.png"),
                32: ("Forbidden Jungle", ["<:ForbiddenJungle:711430596571955363>", "<:forbiddenJungleKey:711443611794800670>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Mixcoatl%20the%20Masked%20God.png"),
                33: ("Snake Pit", ["<:SnakePitPortal:561248700291088386>", "<:snakePitKey:561248916734083075>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Stheno%20the%20Snake%20Queen.png"),
                34: ("Spider Den", ["<:SpiderDen:711430596567760957>", "<:spiderDenKey:711443611371175978>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Arachna%20the%20Spider%20Queen.png"),
                35: ("Forest Maze", ["<:ForestMaze:711430596752179241>", "<:forestMazeKey:711443611568439367>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Mama%20Mothra.png"),
                36: ("Pirate Cave", ["<:PirateCavePortal:574080648000569353>", "<:pirateCaveKey:711443611429896245>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Dreadstump%20the%20Pirate%20King.png"),
                37: ("Beachzone", ["<:BeachzonePortal:711430895051079740>", "<:beachzoneKey:711444566103949392>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Masked%20Party%20God.png"),
                38: ("Belladonnas Garden", ["<:BelladonnasGardenPortal:561248700693741569>", "<:BelladonnasGardenKey:561248916830552067>"],
                     "https://i.imgur.com/d7xzYLG.png"),
                39: ("Ice Tomb", ["<:IceTombPortal:561248700270116869>", "<:iceTombKey:561248917082079272>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Ice%20Tomb%20Defender.png"),
                40: ("Battle Nexus", ["<:BattleNexusPortal:561248700588883979>", "<:battleOfTheNexusKey:561248916570505219>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Oryx%20the%20Mad%20God%20Deux.png"),
                41: ("Red Aliens", ["<:AlienRed:711431346698059858>", "<:alienRedKey:711445699392438302>"],
                     "https://i.imgur.com/BLPokRW.png"),
                42: ("Blue Aliens", ["<:AlienBlue:711431346740002878>", "<:alienBlueKey:711445699241312259>"],
                     "https://i.imgur.com/TQOdFo6.png"),
                43: ("Green Aliens", ["<:AlienGreen:711431347029409853>", "<:alienGreenKey:711445699308290068>"],
                     "https://i.imgur.com/BEToOal.png"),
                44: ("Yellow Aliens", ["<:AlienYellow:711431347108839424>", "<:alienYellowKey:711445699195043850>"],
                     "https://i.imgur.com/C3kJ0x8.png"),
                45: ("Shaitan's Lair", ["<:LairofShaitanPortal:561248700828090388>", "<:shaitansKey:561248917191131152>"],
                     "https://i.imgur.com/azzD6jD.png"),
                46: ("Puppet Master's Encore", ["<:PuppetEncorePortal:561248700723101696>", "<:puppetMastersEncoreKey:561248917082079252>"],
                     "https://static.drips.pw/rotmg/wiki/Enemies/Puppet%20Master%20v2.png"),
                47: ("Cnidarian Reef", ["<:Reef:561250455284350998>", "<:reefKey:561251664388947968>"], "https://i.imgur.com/BF2DclQ.png"),
                48: ("Secluded Thicket", ["<:thicket:561248701402578944>", "<:thicketKey:561248917208039434>"],
                     "https://i.imgur.com/xFWvgyV.png"),
                49: ("Heroic UDL", ["<:HUDL:711479365602508820>", "<:hudlKey:711444346334871643>"], "https://i.imgur.com/WmL1qda.png"),
                50: ("Heroic Abyss", ["<:HAbyss:711431861678637129>", "<:habbyKey:711444346263830559>"], "https://i.imgur.com/LCALe5V.png"),
                }
    if not num:
        return dungeons
    else:
        res = dungeons.get(num)
        if not res:
            return dungeons
        if len(res[1]) == 2:
            return tuple((res[0], res[1] + defaults, res[2]))
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