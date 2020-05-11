# Rotmg-Discord-Bot
Discord bot for ROTMG Verification &amp; AFK Checks

Please contact me on discord (Darkmatter#7321) if you'd like the bot added to your server.

-----
# Requirements
- [github.com/Jacobvs/Realmeye-API](https://github.com/Jacobvs/RealmEye-API)
- Discord.py
- python3
- MySQL
- Cloudinary

-----

# Writeup on Commands:
`<> `means required arugment. `[]` means optional. Do not include `<>` or `[]` when running the command.

FOR CHANNEL ARGUMENT: `1` = Realm Clearing, `2 & 3` = General Raiding, `vet` = Endgame Raiding 1

```Raiding```

***AFK Check***: `!afk <run_type> <channel> [location]`
⇒ Description: Start an AFK Check for the specified run type.
⇒ Aliases: `None`
⇒ Permissions Needed: 
    - Channels `1-3`: @Realm Leader or higher
    - Channel `vet`: @Raid Leader  or higher
⇒ Examples: 
    - `!afk fskipvoid vet USS Left Bazzar`
    - `!afk fametrain 2 USW Gargoyle`
⇒ Notes:
    - Valid run types at the moment are: `void, fskipvoid, cult, nest, realmclear, & fametrain` (I'll be adding more soon)

***Headcount***: `!headcount <run_type> <channel>`
⇒ Description: Start a headcount for the specified run type
⇒ Aliases: `!hc`
⇒ Permissions Needed: Same as AFK Checks (Channel Dependent)
⇒ Examples:
    - `!headcount void 2`
    - `!hc void vet`
    ~ `!hc realmclear 1`
⇒ Notes:
    - It's best to use this to see how many people would come to a run, but don't bait the raiders and not do a run too often please!

***Lock/Unlock**: `!lock <channel>` or `!unlock <channel>`
⇒ Description: Lock/Unlock a specified voice channel
⇒ Permissions Needed: Same as AFK Checks (Channel Dependent)
⇒ Examples:
    - `!lock 1`
    - `!unlock 2`
    - `!lock vet`
⇒ Notes:
    - This command should rarely be used, as the bot locks & unlocks channels dynamically.

***Realm Clearing***: `!realmclear <world_num> <channel> [location]`
⇒ Description: Start a realm clearing run
⇒ Aliases: `!rc`
⇒ Permissions Needed: Same as Afk Checks (Channel Dependent)
⇒ Examples:
    - `!realmclear W3 1 USW Gargoyle`
    - `!rc W3 1 USW Djinn`
    - `!rc 3 vet Australia Spider`
⇒ Notes:
    - ***At the moment, only 1 realmclearing can run at a time per server***, I'll be updating this soon to allow for multiple afk's! (this is due to how map uploading works)
    - The `W` in world_num is optional.
    - The `!markmap`, `!unmarkmap` and `!eventspawn` commands are tied to the realmclearing session & can only be used when an AFK is up.

***Mark Map / Un-mark Map***: `!markmap <number(s)>` or `!unmarkmap <number(s)>`
⇒ Description: Used to dynamically mark spawns in a realm clearing session
⇒ Aliases: `!mm` and `!umm`
⇒ Permissions Needed: @Map Marker or higher
⇒ Examples:
    - `!mm 20`
    - `!mm 1-10`
    - `!mm 1 2 3 4 5 6-10`
    - `!umm 1 2`
⇒ Notes:
    - Any combination of the number formats above is valid
    - It's generally a better idea to do fewer markmap commands that have larger amounts of numbers in them to reduce stress on the bot
      (Instead of doing !mm for each number do !mm <numbers>)
    - Occasionally, maps won't update due to discord errors - ***If this happens, just run the command again!***

***Event Spawn***: `!eventspawn <event>`
⇒ Description: Mark when an event spawns in the realm
⇒ Aliases: `!es`
⇒ Permissions Needed: @Map Marker or higher
⇒ Examples
    - `!eventspawn cube`
    - `!es lotll`
    - `!es avatar`
⇒ Notes:
    - The valid event names are as follows:
    `ava, avatar, cube, cubegod, gship, sphinx, herm, hermit, lotll, lord, pent, penta, drag, rock, skull, shrine, skullshrine, miner, dwarf, sentry, nest, statues`
    - If you type `ship` instead of `gship` or can't spell sphinx – no worries! The bot will attempt to correct to the nearest event!


```Moderation```

***Change Prefix***: `!change_prefix <new_prefix>`
⇒ Description: Changes the bot's prefix for all commands
⇒ Aliases: `None`
⇒ Permissions Needed: Administrator permission
⇒ Examples
    - `!change_prefix +`

***Find***: `!find <user>`
⇒ Description: Find someone in the discord
⇒ Aliases: `None`
⇒ Permissions Needed: @Raid Leader or higher
⇒ Examples
    - `!find darkmattr`
    - `!find oogaboogaiscool`
⇒ Notes:
    - This command shows if they're in a VC, gives a link to their realmeye, & mentions them so you can manage them in discord

***Purge***: `!purge <number> [keep_pinned]`
⇒ Description: Removes a number of messages from the channel it's used in
⇒ Aliases: `None`
⇒ Permissions Needed: Manage Messages Permission
⇒ Examples
    - `!purge 5`
    - `!purge 100 1` (Keeps pinned messages)
⇒ Notes:
    - If you add a `1` after the number of messages, pinned messages will not be deleted.
    - Discord doesn't allow bot's to delete messages older than 15 days. It will stop deleting when it reaches messages that old.

***Nuke***: `!nuke`
⇒ Description: Removes all messages from the channel it's used in
⇒ Aliases: `None`
⇒ Permissions Needed: Administrator Permission
⇒ Examples
    - `!nuke`
    - `!nuke "I confirm this action"`
⇒ Notes:
    - Should rarely, if ever, be used

*** ***: ``
⇒ Description: 
⇒ Aliases: ``
⇒ Permissions Needed:
⇒ Examples
    -
⇒ Notes:
    -

***Manual Verify***: `!manual_verify <@member> <ign>`
⇒ Description: Manually verify someone without them going through the bot's messages
⇒ Aliases: `None`
⇒ Permissions Needed: Manage roles permission, or used in the manual_verify channel.
⇒ Examples
    - `!manual_verify @Darkmatter Darkmattr`
    - `!manual_verify @ConsoleMC HeyitsConsole`
⇒ Notes:
    - If you use this command in the channel that @Ooga-Booga sends manual_verifications in - it doesn't check perms.

***Manual Verify Deny***: `!manual_verify_deny <@member>`
⇒ Description: Deny someone from verifying
⇒ Aliases: `None`
⇒ Permissions Needed: Manage roles permission, or used in the manual_verify channel.
⇒ Examples
    - `!manual_verify_deny @darkmattr`
⇒ Notes:
    - Should rarely need to use this

***Mute***: `!mute <@member> [time] [reason] `
⇒ Description: Mute someone for an amount of time
⇒ Aliases: `None`
⇒ Permissions Needed: Kick Members permission
⇒ Examples
    - `!mute @Darkmattr 15m spam`
    - `!mute @Darkmattr 10d`
    - `!mute @Darkmattr`
⇒ Notes:
    - Time defaults to 15 minutes if not specified
    - Time is done by appending (`d` for days, `h` for hours, `m` for minutes, `s` for seconds) directly to the number

***Un-Mute***: `!unmute <@member>`
⇒ Description: Unmute someone
⇒ Aliases: `None`
⇒ Permissions Needed: Kick Members permission
⇒ Examples
    - `!unmute @Darkmattr`


```Verification```

***Add Verification Message***: `!add_verify_msg`
⇒ Description: Adds the verification message to the channel it's used in
⇒ Aliases: `None`
⇒ Permissions Needed: Manage Server permission
⇒ Examples
    - `!add_verify_msg`
⇒ Notes:
    - Using this command will make the old verify message stop working


```Music```

***Play***: `!play <song name/url>`
⇒ Description: Adds song to queue and plays music
⇒ Aliases: `!p`
⇒ Permissions Needed: @DJ role
⇒ Examples
    - `!p never gonna give you up`
    - `!p <youtube song link>`
    - `!p <youtube playlist link>`
⇒ Notes:
    - You have to be in a voice channel to use this command.
    - Use `!nowplaying` or `!np` to see the music control panel

***General Music Commands***: 
⇒ Description: These should all be self explanitory
⇒ Permissions Needed: @DJ role
⇒ Examples
    - `!pause`
    - `!leave`
    - `!volume <0-250>` or `!vol`
    - `!skip`
    - `!queue` or `!q`
    - `!clearqueue` or `!clear`
    - `!jumpqueue <index> <new_index>` - Moves song at index to new_index in the queue



Minigames & Casino Commands can be seen with:
`!help Minigames`
`!help Casino`

-----
# Verification
Examples of verifying with the bot
Features:
- Configurable requirements (# 8/8's, # Stars, # Alive Fame, Account Creation Date, Private Location, etc)
- Cross-Server Verification
- Automatic Verification Appeals
- Name History Checks
- & More!

![](https://i.imgur.com/UT8pK7D.png)
![](https://i.imgur.com/WpCK1sm.png)
![](https://i.imgur.com/XEb9irx.png)
![](https://i.imgur.com/lYxU2jl.png)
![](https://i.imgur.com/tqjdDYc.png)
----
# Raiding
Examples of Raid announcements
Features:
- Supports any dungeon type
- Control panel to monitor keys, etc
- DM's Location to key/vial/etc.

![](https://i.imgur.com/TTazLL5.png)
![](https://i.imgur.com/lKxb2qX.png)
![](https://i.imgur.com/BaEtE6q.png)
![](https://i.imgur.com/RZcvxUc.png)
-----
# Miscellaneous
A few examples of Miscellaneous Commands and Features

![](https://i.imgur.com/OyOaBqI.png)
![](https://i.imgur.com/1t7FUCW.png)
![](https://i.imgur.com/bpFc4rL.png)
