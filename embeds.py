from datetime import datetime

import discord

# Verification
import utils


def verification_check_msg(reqs, support_channel_name):
    embed = discord.Embed(title='Verification Steps',
                          description="__If you meet the requirements of this server, follow these steps to be verified:__\n1. Enable "
                                      "DM's from server members\n2. Set **everything** on Realmeye to public except last known "
                                      "location\n3. React to the ✅ below\n4. Follow all the directions the bot DM's you.",
                          color=discord.Color.green())
    embed.add_field(name="Server Requirements", value=f"```yaml\n{reqs}```")
    embed.add_field(name="Troubleshooting", value=f"If you're having trouble verifying, post in #{support_channel_name}!", inline=False)
    return embed


def verification_dm_start():
    embed = discord.Embed(title="Verification Status", color=discord.Color.teal())
    embed.description = "__You are not yet verified. Follow the steps below to gain access to the " \
                        "server.__ "
    embed.add_field(name="\a", value="**Please provide your IGN** as it is spelled in-game.\nOnly "
                                     "send your IGN, ex: `Darkmattr`\n\nCapitalization does not "
                                     "matter.")
    embed.set_footer(text="React to the 'X' to cancel verification.")
    return embed


def verification_step_1(ign):
    embed = discord.Embed(title="Verification Status", description="Is `{}` the correct username?".format(ign), color=discord.Color.teal())
    embed.add_field(name='https://www.realmeye.com/player/{}'.format(ign),
                    value="React with the check if so, if you entered the wrong username - click the x to cancel verification then dm the bot your correct username.")
    return embed


def verification_step_2(ign, key):
    embed = discord.Embed(title="You're almost done!", description="You have chosen `{}` to be your IGN.".format(ign),
                          color=discord.Color.teal())
    embed.add_field(name="\a", value="Please paste the code below into any line of your [realmeye]("
                                     "https://www.realmeye.com/player/{}) description.\n```{}```\n\nOnce you are done, "
                                     "un-react to the check emoji and re-react to finish!".format(ign, key))
    return embed


def verification_success(guild_name, mention):
    embed = discord.Embed(title="Success!", description="{} is now a verified member of __{}__!".format(mention, guild_name),
                          color=discord.Color.green())
    return embed


def verification_denied(mention, denier_mention):
    embed = discord.Embed(title="Verification Denied",
                          description=f"{mention} - Your verification appeal has been denied by: {denier_mention}\n If you truly think this is an error please contact a moderator+.",
                          color=discord.Color.red())
    return embed


def verification_already_verified():
    embed = discord.Embed(title="Verification Status", color=discord.Color.teal())
    embed.description = "__You are already verified!__"
    embed.add_field(name="Troubleshooting", value="If there are still missing channels, please contact a "
                                                  "moderator+!")
    return embed


def verification_already_verified_complete(verified_servers, ign):
    embed = discord.Embed(title="Verification Status", color=discord.Color.teal())
    embed.description = "__You have been verified in another server__"
    if verified_servers is not None:
        embed.add_field(name="Verified Servers:", value='`{}`'.format(verified_servers))
    embed.add_field(name="\a", value="React with a thumbs up if you would like to verify for this server with the IGN: `{}`.".format(ign),
                    inline=False)
    return embed


def verification_checking_realmeye():
    embed = discord.Embed(title="Retrieving data from Realmeye...", color=discord.Color.green())
    return embed


def verification_manual_verify(user, ign, code, fame, nfame, nfamereq, maxed, nmaxed, nmaxedreq, stars, nstars, nstarsreq, months, nmonths,
                               nmonthsreq, private):
    embed = discord.Embed(title="Manual Verification",
                          description=f"{user} with the ign: {ign} - ([Realmeye Link](https://www.realmeye.com/player/{ign})) failed to meet the requirements and would like "
                                      f"to be manually verified.\nThe code they were provided is: `{code}`")
    embed.add_field(name="Fame", value=bool_to_emoji(fame) + f" ({nfame}/{nfamereq} fame)", inline=True)
    embed.add_field(name="Maxed Characters", value=bool_to_emoji(maxed) + f" ({nmaxed}/{nmaxedreq} maxed)", inline=True)
    embed.add_field(name="Stars", value=bool_to_emoji(stars) + f" ({nstars}/{nstarsreq} stars)", inline=True)
    embed.add_field(name="Account Creation Date", value=bool_to_emoji(months) + f" ({nmonths}/{nmonthsreq} months)", inline=True)
    embed.add_field(name="Private Location", value=bool_to_emoji(private), inline=True)
    embed.add_field(name='\a', value='\a', inline=True)
    embed.add_field(name='Command:', value=f'To manually verify them use the check, to deny them use the X.', inline=False)
    return embed


# Verification Errors

def verification_missing_code(key):
    embed = discord.Embed(title="Error!", description="You do not appear to have the code in your description.", color=discord.Color.red())
    embed.add_field(name="\a",
                    value=f"The code you were provided is: `{key}`\nIf you have already placed the code in your description, wait a minute for the servers to "
                          "catch up and re-react to the check above.")
    return embed


def verification_public_location():
    embed = discord.Embed(title="Error!", description="Your location has not been set to private.", color=discord.Color.red())
    embed.add_field(name="\a", value="Once you've set your location to private, wait a minute for the servers to catch up and "
                                     "re-react to the check above.")
    return embed


def verification_private_chars():
    embed = discord.Embed(title="Error!", description="Your character list has been set to private.", color=discord.Color.red())
    embed.add_field(name="\a", value="Once you've set your characters to public, wait a minute for the servers to catch up and "
                                     "re-react to the check above.")
    return embed


def verification_private_time():
    embed = discord.Embed(title="Error!", description="Your profile creation date has been set to private.", color=discord.Color.red())
    embed.add_field(name="\a", value="Once you've set your creation date to public, wait a minute for the servers to catch up and "
                                     "re-react to the check above.")
    return embed


def bool_to_emoji(b):
    if b:
        return '✅'
    return '❌'


def verification_bad_reqs(requirements, fame, maxed, stars, months, private):
    embed = discord.Embed(title="Error!", description="You do not meet the requirements for this server!", color=discord.Color.red())
    embed.add_field(name='Requirements:', value="```yaml\n{}```".format(requirements), inline=False)
    embed.add_field(name="Fame", value=bool_to_emoji(fame), inline=True)
    embed.add_field(name="Maxed Characters", value=bool_to_emoji(maxed), inline=True)
    embed.add_field(name="Stars", value=bool_to_emoji(stars), inline=True)
    embed.add_field(name="Account Creation Date", value=bool_to_emoji(months), inline=True)
    embed.add_field(name="Private Location", value=bool_to_emoji(private), inline=True)
    embed.add_field(name='\a', value='\a', inline=True)
    embed.add_field(name="\a", value="**If you would like to appeal the verification to a mod, __re-react to the check or thumbs-up emoji "
                                     "in this message.__**",
                    inline=False)
    embed.set_footer(
        text="React to the 'X' to cancel verification (if you would like to retry - cancel then react to the message in the server again.")
    return embed


def verification_bad_username():
    embed = discord.Embed(title="Error!",
                          description="The username you provided is invalid or has been taken. Please re-submit your username __as it is spelled in-game.__",
                          color=discord.Color.red())
    return embed


def verification_cancelled():
    embed = discord.Embed(title="Verification Cancelled.",
                          description="You have cancelled the verification process.\nIf you would like to restart, re-react to the "
                                      "verification message in the server.", color=discord.Color.red())
    return embed


# Subverification

def subverify_msg(name, support_channel_name):
    embed = discord.Embed(title=f"Verification for {name}",
                          description="Click the ✅ emoji below to gain access to this category, or the ❌ to remove it.",
                          color=discord.Color.green())
    embed.add_field(name="Troubleshooting", value=f"If you're having trouble verifying, post in #{support_channel_name}!", inline=False)
    return embed


# Misc
def poll(title, options):
    numbers = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🔟']
    embed = discord.Embed(title=f"🗳️ Poll: {title.capitalize()}", color=discord.Color.dark_gold())
    desc = ""
    for i, o in enumerate(options):
        desc += numbers[i] + ": " + options[i] + "\n"
    embed.description = desc
    return embed


# Raiding

def headcount_base(run_title, requester, keyed_run, emojis, thumbnail=None):
    if keyed_run:
        desc = (f"React with {emojis[0]} to participate and {emojis[1]} if you have a key and are willing to pop it!\n"
                "To indicate your class or gear choices, react to the appropriate emoji's below")
    else:
        desc = ((f"React with {emojis[0]} to participate in the run!\n"
                 "To indicate your class or gear choices, react to the appropriate emoji's below"))
    embed = discord.Embed(description=desc, color=discord.Color.teal())
    embed.set_author(name=f"Headcount for {run_title} started by {requester.nick}", icon_url=requester.avatar_url)
    embed.set_footer(text="Headcount started ")
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.timestamp = datetime.utcnow()
    return embed


def afk_check_base(run_title, requester, keyed_run: bool, emojis, thumbnail=None):
    if keyed_run:
        desc = (f"To join, **connect to the raiding channel by clicking its name** and react to: {emojis[0]}\n"
                f"If you have a key, react to {emojis[1]}\n"
                "To indicate your class or gear choices, react to the appropriate emoji's below\n"
                "To end the AFK check as a leader, react to ❌")
    else:
        desc = (f"To join, **connect to the raiding channel by clicking its name** and react to: {emojis[0]}\n"
                "To indicate your class or gear choices, react to the appropriate emoji's below\n"
                "To end the AFK check as a leader, react to ❌")
    embed = discord.Embed(description=desc, color=discord.Color.teal())
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
    embed.set_author(name=f"{run_title} started by {requester.display_name}", icon_url=requester.avatar_url)
    embed.set_footer(text="Time remaining: 6 minutes and 0 seconds | Raiders accounted for: 1")
    return embed


def afk_check_control_panel(msg_url, location, run_title, key_emoji, keyed_run):
    embed = discord.Embed(description=f"**[AFK Check]({msg_url}) control panel for `{run_title}`**", color=discord.Color.teal())
    embed.add_field(name="Location of run:", value=location, inline=False)
    embed.add_field(name="Nitro Boosters:", value=f"`None`", inline=True)
    if keyed_run:
        embed.add_field(name="Current Keys:", value=f"Main {key_emoji}: None\nBackup {key_emoji}: None", inline=False)
    if run_title == "Void" or run_title == "Full-Skip Void":
        embed.add_field(name="Vials:", value="Main <:vial:682205784524062730>: None\nBackup <:vial:682205784524062730>: None",
                        inline=False)
    elif run_title == "Oryx 3":
        embed.add_field(name="Sword Rune", value="Main <:SwordRune:708191783405879378>: \nBackup <:SwordRune:708191783405879378>: ",
                        inline=True)
        embed.add_field(name="Shield Rune", value="Main <:ShieldRune:708191783674314814>: \nBackup <:ShieldRune:708191783674314814>: "
                       , inline=True)
        embed.add_field(name="Helm Rune", value="Main <:HelmRune:708191783825178674>: \nBackup <:HelmRune:708191783825178674>: ",
                        inline=True)
    if run_title == "Realm Clearing":
        embed.add_field(name="Cleared Numbers:", value="`[None]`")
    embed.set_footer(text="AFK Check started ")
    embed.timestamp = datetime.utcnow()
    return embed


def fame_train_afk(user, vc, world_num):
    embed=discord.Embed(title=f"World {world_num}", description="Join the train channel and react with <:fame:682209281722024044> "
                        "to not be moved out.\nTo indicate your class or gear choices, react with <:sorcerer:682214487490560010>"
                        "<:necromancer:682214503106215966><:sseal:683815374403141651><:puri:682205769973760001>\nIf you are Nitro Boosting "
                        "the server, react to <:nitro:706246225200152656>\nTo end the fame train as a conductor, react to :x:",
                        url=world_move_urls(world_num), color=discord.Color.orange())
    embed.set_author(name=f"Fame Train started by {user.display_name} in {vc.name}", icon_url=user.avatar_url)
    embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/679309966128971797/696452960825376788/fame2.png")
    embed.set_footer(text="Trainers Accounted for: 1")
    embed.timestamp = datetime.utcnow()
    return embed

def world_move_urls(num):
    return "https://cdn.discordapp.com/attachments/705911989334966362/710364667364638730/W12_Pfeil_gif.gif" if num == 12 \
    else "https://cdn.discordapp.com/attachments/705911989334966362/710362677997862952/W10_pfeil_gif.gif" if num == 10 \
    else "https://cdn.discordapp.com/attachments/705911989334966362/706960033728036944/Weg_Gif_Pfeil.gif" if num == 3 \
    else "https://cdn.discordapp.com/attachments/705911989334966362/710360114346983424/W1_Pfeil_gif.gif"
# CASINO

def roulette_help_embed():
    embed = discord.Embed(title="Roulette", color=discord.Color.orange()).add_field(name="Bet Types",
                                                                                    value="black/red/green/high/low/even/odd, 0-36", inline=False)\
        .add_field(
        name="Winnings", value="**Black/Red** - x2\n**Green** - x18\n**1-36** - x35\n**High/Low** - x2\n**Even/Odd** - x2", inline=False).add_field(
        name="Numbers",
        value="Green: **0, 0** (2x the chance)\nBlack: **2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35**\n"
              "Red: **1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36**\nLow: **1-18**\nHigh: **19-36**", inline=False).add_field(
        name="Usage", value="!roulette [bet_type] [bet]", inline=False)
    return embed

def slots_help_embed():
    embed = discord.Embed(title="Slots", color=discord.Color.orange()).add_field(name="Info", value="Roll the slot machine and watch the "
                        "credits pour in!\nTo win, match three symbols in the middle row.", inline=False)\
                        .add_field(name="Winnings", value=":lemon: Lemon - **2x**\n:watermelon: Melon - **3x**\n:banana: Banana - **5x**"
                                                          "\n:cherries: Cherry - **10x**\n:gem: Diamond - **40x**\n"
                                                          "<:slot7:711843601369530458> 7's - **100x**", inline=False)\
                        .add_field(name="Odds", value=":x: Lose - **80%** (Tickets 1-799)\n:lemon: Lemon - **10%** (800-899)"
                                                      "\n:watermelon: Melon - **4%** (900-939)\n:banana: Banana - **3%** (940-969)"
                                                          "\n:cherries: Cherry - **1.5%** (970-984)\n:gem: Diamond - **1%** (985-994)\n"
                                                          "<:slot7:711843601369530458> 7's - **0.5%** (995-1000)", inline=False)\
                        .add_field(name="Usage", value="!slots <bet>", inline=False)
    return embed


def dungeon_select(hc=False):
    descrip = "Please select a dungeon type by typing the number corresponding to the  dungeon for which you would like to start a raid.\n" \
              "To start a random dungeon headcount type: `(0)` <:defaultdungeon:682212333182910503> Random Dungeons." if hc else \
        "Please select a dungeon type by typing the number corresponding to the  dungeon for which you would like to start a raid."

    embed = discord.Embed(title="Dungeon Selection", description=descrip,
                          color=discord.Color.orange())
    dungeons = utils.dungeon_info()
    endgame = ""
    realmrelated = ""
    midtier = ""
    lowtier = ""
    other = ""
    mini = ""
    for i, d in enumerate(dungeons.values(), 1):
        if i < 8:
            endgame += f"`({i})` {d[1][0]} {d[0]}\n"
        elif i < 17:
            realmrelated += f"`({i})` {d[1][0]} {d[0]}\n"
        elif i < 27:
            midtier += f"`({i})` {d[1][0]} {d[0]}\n"
        elif i < 37:
            lowtier += f"`({i})` {d[1][0]} {d[0]}\n"
        elif i < 45:
            other += f"`({i})` {d[1][0]} {d[0]}\n"
        else:
            mini += f"`({i})` {d[1][0]} {d[0]}\n"

    embed.add_field(name="Endgame Dungeons", value=endgame, inline=True)
    embed.add_field(name="Realm-Related Dungeons", value=realmrelated, inline=True)
    embed.add_field(name="Mid-Tier Dungeons", value=midtier, inline=True)
    embed.add_field(name="Low-Tier Dungeons", value=lowtier, inline=True)
    embed.add_field(name="Misc. Dungeons", value=other, inline=True)
    embed.add_field(name="Mini Dungeons", value=mini, inline=True)
    return embed