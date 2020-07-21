import enum
import json
from datetime import datetime, timedelta


async def get_user(pool, uid):
    """Return user data from rotmg.users table"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.users WHERE id = {uid}")
            data = await cursor.fetchone()
            await conn.commit()
            return data


async def get_num_verified(pool):
    """Count number of verified raiders"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM rotmg.users where status = 'verified'")
            data = await cursor.fetchone()
            await conn.commit()
            return data

async def ign_exists(pool, ign, id):
    """Check if an IGN has been entered into the user table already"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.users WHERE ign = '{}' AND status = 'verified'".format(ign))
            user = await cursor.fetchone()
            await conn.commit()
            if not user or user[0] == id:
                return False
            return True

async def get_user_from_ign(pool, name):
    """Retrieve User Data From IGN"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "SELECT * from rotmg.users WHERE (ign = %s OR alt1 = %s OR alt2 = %s) AND status = 'verified'"
            data = (name, name, name)
            await cursor.execute(sql, data)
            user = await cursor.fetchone()

            return user

async def add_alt_name(pool, uid, altname):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "SELECT * from rotmg.users WHERE id = %s AND status = 'verified'"
            data = (uid)
            await cursor.execute(sql, data)
            data = await cursor.fetchone()
            if not data:
                return False
            if data[usr_cols.alt1]:
                if data[usr_cols.alt2]:
                    return False
                else:
                    t = 'alt2'
            else:
                t = 'alt1'
            sql = f"UPDATE rotmg.users SET {t} = %s WHERE id = %s"
            data = (altname, uid)
            await cursor.execute(sql, data)
            await conn.commit()
            return True

async def remove_alt_name(pool, uid, altname):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "SELECT * from rotmg.users WHERE id = %s AND status = 'verified'"
            data = (uid)
            await cursor.execute(sql, data)
            data = await cursor.fetchone()
            if not data:
                return False
            movealts=False
            if data[usr_cols.alt1] and data[usr_cols.alt1].lower() == altname.lower():
                t = 'alt1'
                if data[usr_cols.alt2]:
                    movealts=True
            elif data[usr_cols.alt2] and data[usr_cols.alt2].lower() == altname.lower():
                t = 'alt2'
            else:
                return False

            if not movealts:
                sql = f"UPDATE rotmg.users SET {t} = %s WHERE id = %s"
                data = (None, uid)
            else:
                sql = f"UPDATE rotmg.users SET alt1 = %s, alt2 = %s WHERE id = %s"
                data = (data[usr_cols.alt2], None, uid)
            await cursor.execute(sql, data)
            await conn.commit()
            return True

async def get_blacklist(pool, uid, gid, type=None):
    """Get Blacklist entry for user or get all entries"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            if type:
                sql = "SELECT * FROM rotmg.blacklist WHERE uid = %s AND gid = %s AND type = %s"
                data = (uid, gid, type)
                await cursor.execute(sql, data)
                await conn.commit()
                res = await cursor.fetchone()
                return True if res else False
            else:
                sql = "SELECT * FROM rotmg.blacklist WHERE uid = %s AND gid = %s"
                data = (uid, gid)
                await cursor.execute(sql, data)
                await conn.commit()
                res = await cursor.fetchall()
                return res


async def add_blacklist(pool, uid, gid, rid, type, reason):
    """Add Blacklist entry for user"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "INSERT INTO rotmg.blacklist (uid, gid, rid, type, reason) VALUES (%s, %s, %s, %s, %s)"
            data = (uid, gid, rid, type, reason)
            await cursor.execute(sql, data)
            await conn.commit()

async def remove_blacklist(pool, uid, gid, type):
    """Add Blacklist entry for user"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "DELETE FROM rotmg.blacklist WHERE uid = %s AND gid = %s AND type = %s"
            data = (uid, gid, type)
            await cursor.execute(sql, data)
            await conn.commit()


async def add_new_user(pool, user_id, guild_id, verify_id):
    """Create record of user data in rotmg.users"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "INSERT INTO rotmg.users (id, status, verifyguild, verifyid) VALUES (%s, 'stp_1', %s, %s)"
            data = (user_id, guild_id, verify_id)
            await cursor.execute(sql, data)
            await conn.commit()


async def update_user(pool, id, column, change):
    """Update user data entry in rotmg.users"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "UPDATE rotmg.users SET {} = %s WHERE id = {}".format(column, id)
            await cursor.execute(sql, (change,))
            await conn.commit()


## GUILD Functions

async def add_new_guild(pool, guild_id, guild_name):
    """Add new guild to rotmg.guilds"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = ("INSERT INTO rotmg.guilds (id, name, verificationid, nmaxed, nfame,"
                   "nstars, reqall, privateloc, reqsmsg, manualverifychannel, verifiedroleid,"
                   "verifylogchannel) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            data = (guild_id, guild_name, 0, 0, 0, 0, False, True, "", 0, 0, 0)
            await cursor.execute(sql, data)
            await conn.commit()
            sql = "INSERT INTO `rotmg`.`casino_top` (`guildid`, `1_id`, `1_bal`, `2_id`, `2_bal`, `3_id`, `3_bal`, `4_id`, `4_bal`," \
                  " `5_id`, `5_bal`, `6_id`, `6_bal`, `7_id`, `7_bal`, `8_id`, `8_bal`, `9_id`, `9_bal`, `10_id`, `10_bal`) VALUES " \
                  f"({guild_id}, NULL, DEFAULT, NULL, DEFAULT, NULL, DEFAULT, NULL, DEFAULT, NULL, DEFAULT, NULL, DEFAULT, NULL, " \
                  "DEFAULT, NULL, DEFAULT, NULL, DEFAULT, NULL, DEFAULT)"
            await cursor.execute(sql)
            await conn.commit()


async def update_guild(pool, id, column, change):
    """Update guild data in rotmg.guilds"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = f"UPDATE rotmg.guilds SET {column} = %s WHERE id = %s"
            await cursor.execute(sql, (change, id))
            await conn.commit()

async def get_guild(pool, gid):
    """Return guild data from rotmg.guilds"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.guilds WHERE id = {gid}")
            data = await cursor.fetchone()
            await conn.commit()
            return data

async def get_guilds(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.guilds")
            data = await cursor.fetchall()
            await conn.commit()
            return data


async def construct_guild_database(pool, client, guildid=None):
    if not guildid:
        guilds = await get_guilds(pool)
        guild_db = {}
    else:
        guild_db = client.guild_db
        guilds = get_guild(pool, guildid)
    for i, g in enumerate(guilds):
        db = {}
        guild = client.get_guild(g[0])
        if guild:
            for j, r in enumerate(g):
                if r:
                    if j in gdb_channels:
                        db[j] = guild.get_channel(r)
                    elif j in gdb_roles:
                        db[j] = guild.get_role(r)
                    else:
                        db[j] = r
                else:
                    db[j] = None
            guild_db[g[0]] = db
    return guild_db

# CASINO Functions

async def get_casino_player(pool, id):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.casino WHERE id = {id}")
            data = await cursor.fetchone()
            await conn.commit()
            if not data:
                now = datetime.utcnow()
                now = now.strftime('%Y-%m-%d %H:%M:%S')
                sql = ("INSERT INTO rotmg.casino (id, balance, dailycooldown, workcooldown, searchcooldown) VALUES (%s, %s, %s, %s, %s)")
                data = [id, 7500, now, now, now]
                await cursor.execute(sql, data)
                await conn.commit()
                for i, d in enumerate(data):
                    if i > 1:
                        data[i] = datetime.strptime(d, '%Y-%m-%d %H:%M:%S')
            return data


async def change_balance(pool, guild_id, id, new_bal):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * FROM rotmg.casino_top where guildid = {guild_id}")
            data = list(await cursor.fetchone())
            leaderboard_size = 10
            if data[-1] <= new_bal:
                # Split the data out into relevant parts
                g_id = data[0]
                data = data[1:]
                uids = data[::2]
                bals = data[1::2]
                # Build balance uid pairs
                data = [[u, b] for u, b in zip(uids, bals)]
                uid_loc = None

                # Index throws up when not found
                try:
                    uid_loc = uids.index(id)
                except:
                    pass

                if uid_loc is not None:
                    data[uid_loc][1] = new_bal
                else:
                    data.append((id, new_bal))

                # Remove any entry with None
                data = list(filter(lambda x: x[0] is not None, data))
                # Sort by balance
                data = sorted(data, key=lambda x: x[1], reverse=True)

                # Append so data is 10 long
                if len(data) < leaderboard_size:
                    data = [*data, *[[None, 0]] * (leaderboard_size - len(data))]
                # Chop to 10
                data = data[:leaderboard_size]

                # De-interleave data
                # Build list
                write_data = list(range(leaderboard_size * 2))
                # Put user ids in even indexes
                write_data[::2] = [pair[0] for pair in data]
                # Put balances in odd indexes
                write_data[1::2] = [pair[1] for pair in data]

                # Add guild id to front
                write_data = [g_id, *write_data]
                # Write to database
                await cursor.execute("REPLACE INTO rotmg.casino_top (guildid, 1_id, 1_bal, 2_id, 2_bal, 3_id, 3_bal, 4_id, 4_bal, 5_id, "
                                     "5_bal, 6_id, 6_bal, 7_id, 7_bal, 8_id, 8_bal, 9_id, 9_bal, 10_id, 10_bal) "
                                     "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", write_data)

            elif id in data and new_bal < data[-1]:
                # Index throws up when not found
                uid_loc = None
                try:
                    uid_loc = data.index(id)
                except:
                    pass

                if uid_loc:
                    del data[uid_loc]
                    del data[uid_loc]
                    data.append(None)
                    data.append(0)
                    await cursor.execute(
                        "REPLACE INTO rotmg.casino_top (guildid, 1_id, 1_bal, 2_id, 2_bal, 3_id, 3_bal, 4_id, 4_bal, 5_id, "
                        "5_bal, 6_id, 6_bal, 7_id, 7_bal, 8_id, 8_bal, 9_id, 9_bal, 10_id, 10_bal) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", data)

            await cursor.execute(f"UPDATE rotmg.casino SET balance = {new_bal} WHERE id = {id}")
            await conn.commit()


async def update_cooldown(pool, id, column):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            time = datetime.utcnow()
            if column == 2:
                column = "dailycooldown"
                time = time + timedelta(days=1)
            elif column == 3:
                column = "workcooldown"
                time = time + timedelta(hours=4)
            elif column == 4:
                column = "searchcooldown"
                time = time + timedelta(minutes=30)
            elif column == 5:
                column = "stealcooldown"
                time = time + timedelta(hours=8)
            else:
                return
            time = time.strftime('%Y-%m-%d %H:%M:%S')
            await cursor.execute(f"UPDATE rotmg.casino SET {column} = '{time}' WHERE id = {id}")
            await conn.commit()

async def get_top_balances(pool, guild_id):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.casino_top WHERE guildid = {guild_id}")
            data = await cursor.fetchone()
            await conn.commit()
            return data


## RUN LOGGING:
async def log_runs(pool, guild_id, member_id, column=1, number=1):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.logging WHERE uid = {member_id} AND gid = {guild_id}")
            data = await cursor.fetchone()
            await conn.commit()
            if not data:
                await cursor.execute(f"INSERT INTO rotmg.logging(uid, gid) VALUES({member_id}, {guild_id})")
                await conn.commit()
                data = 0
            else:
                data = data[column]

            name = "pkey" if column == 1 else "vials" if column == 2 else "helmrunes" if column == 3 else "shieldrunes" if column == 4 else\
                "swordrunes" if column == 5 else "eventkeys" if column == 6 else "runsdone" if column == 7 else "eventsdone" if column == 8\
                else "srunled" if column == 9 else "frunled" if column == 10 else "eventled" if column == 11 else "runsassisted" if\
                column == 12 else "eventsassisted"
            if column == 9 or column == 10 or column == 11:
                await cursor.execute(f"UPDATE rotmg.logging SET {name} = {name} + {number}, weeklyruns = weeklyruns + {number} "
                                     f"WHERE uid = {member_id} AND gid = {guild_id}")
            elif column == 12:
                await cursor.execute(f"UPDATE rotmg.logging SET {name} = {name} + {number}, weeklyassists = weeklyassists + {number} "
                                     f"WHERE uid = {member_id} AND gid = {guild_id}")
            else:
                await cursor.execute(f"UPDATE rotmg.logging SET {name} = {name} + {number} WHERE uid = {member_id} AND gid = {guild_id}")
            await conn.commit()

            return data + number

async def get_log(pool, guild_id, member_id):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.logging WHERE uid = {member_id} AND gid = {guild_id}")
            data = await cursor.fetchone()
            await conn.commit()
            if not data:
                await cursor.execute(f"INSERT INTO rotmg.logging (uid, gid) VALUES({member_id}, {guild_id})")
                await conn.commit()
                await cursor.execute(f"SELECT * from rotmg.logging WHERE uid = {member_id} AND gid = {guild_id}")
                data = await cursor.fetchone()
            return data

async def get_top_10_logs(pool, guild_id, column, only_10=True):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            name = "pkey" if column == 1 else "vials" if column == 2 else "helmrunes" if column == 3 else "shieldrunes" if column == 4 \
                else "swordrunes" if column == 5 else "eventkeys" if column == 6 else "runsdone" if column == 7 else "eventsdone" if \
                column == 8 else "srunled" if column == 9 else "frunled" if column == 10 else "eventled" if column == 11 else \
                "runsassisted" if column == 12 else "eventsassisted" if column == 13 else "weeklyruns" if column == 14 else "weeklyassists"
            if only_10:
                await cursor.execute(f"SELECT * from rotmg.logging WHERE gid = {guild_id} ORDER BY {name} DESC LIMIT 10")
            else:
                await cursor.execute(f"SELECT * from rotmg.logging WHERE gid = {guild_id} ORDER BY {name} DESC")
            data = await cursor.fetchall()
            await conn.commit()
            return list(data)

async def get_0_runs(pool, guild_id):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.logging WHERE gid = {guild_id} AND weeklyruns = 0")
            data = await cursor.fetchall()
            await conn.commit()
            return list(data)

## Punishments
async def add_punishment(pool, uid, gid, type, rid, endtime, reason, roles=None):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            time = endtime.strftime('%Y-%m-%d %H:%M:%S') if endtime else None
            sql = f"INSERT INTO rotmg.punishments (uid, gid, type, r_uid, endtime, reason, presuspendroles) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            data = (uid, gid, type, rid, time, reason, json.dumps(roles))
            await cursor.execute(sql, data)
            await conn.commit()

async def get_suspended_roles(pool, uid, guild):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.punishments WHERE uid = {uid} AND gid = {guild.id} AND type = 'suspend' AND "
                                 "active = TRUE ")
            data = await cursor.fetchone()
            roles = []
            res = json.loads(data[punish_cols.roles])
            for r in res.values():
                roles.append(guild.get_role(r))
            return roles

async def has_active(pool, uid, gid, ptype):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"select exists(select * from rotmg.punishments where uid = {uid} AND gid = {gid} AND type = '{ptype}' "
                                 "and active = TRUE limit 1)")
            data = await cursor.fetchone()
            return True if data[0] >= 1 else False

async def get_all_active_punishments(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM rotmg.punishments WHERE active = TRUE and endtime IS NOT NULL")
            data = await cursor.fetchall()
            return data

async def get_users_punishments(pool, uid, gid):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.punishments WHERE uid = {uid} and gid = {gid} ORDER BY type ASC")
            return await cursor.fetchall()

async def set_unactive(pool, gid, uid, ptype):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"UPDATE rotmg.punishments SET active = FALSE WHERE uid = {uid} AND gid = {gid} AND type = '{ptype}'")
            await conn.commit()


class punish_cols(enum.IntEnum):
    uid = 0
    gid = 1
    type = 2
    r_uid = 3
    starttime = 4
    endtime = 5
    reason = 6
    active = 7
    roles = 8

class blacklist_cols(enum.IntEnum):
    uid = 0
    gid = 1
    rid = 2
    type = 3
    reason = 4
    issuetime = 5

class log_cols(enum.IntEnum):
    id = 0
    gid = 1
    pkey = 2
    vials = 3
    helmrunes = 4
    shieldrunes = 5
    swordrunes = 6
    eventkeys = 7
    runsdone = 8
    eventsdone = 9
    srunled = 10
    frunled = 11
    eventled = 12
    runsassisted = 13
    eventsassisted = 14
    weeklyruns = 15
    weeklyassists = 16

class casino_cols(enum.IntEnum):
    id = 0
    balance = 1
    dailycooldown = 2
    workcooldown = 3
    searchcooldown = 4
    stealcooldown = 5


class usr_cols(enum.IntEnum):
    """Contains References to rotmg.users table for easy access"""
    id = 0  # Int
    ign = 1  # String
    status = 2  # String
    verifyguild = 3  # Int
    verifykey = 4  # String
    verifyid = 5  # Int
    verifiedguilds = 6  # String (CSV)
    alt1 = 7
    alt2 = 8

# Define which DB records are of what type
# Channels (Text, Voice, Category)
gdb_channels = [9, 11, 13, 14, 15, 16, 17, 18, 20, 21, 28, 33, 34, 35, 36, 38, 39, 40, 41, 42, 44, 45, 46, 60, 61]
# Roles
gdb_roles = [10, 19, 22, 23, 27, 31, 32, 37, 43, 47, 48, 50, 52, 54, 58]

class gld_cols(enum.IntEnum):
    """Contains References to rotmg.guilds table for easy access"""
    id = 0  # Int
    name = 1  # String
    verificationid = 2  # Int
    nmaxed = 3  # Int
    nfame = 4  # Int
    nstars = 5  # Int
    reqall = 6  # Boolean
    privateloc = 7  # Boolean
    reqsmsg = 8  # String (formatted)
    manualverifychannel = 9  # Int
    verifiedroleid = 10  # Int
    verifylogchannel = 11  # Int
    supportchannelname = 12  # String
    raidhc1 = 13  # Int
    raidvc1 = 14  # Int
    raidhc2 = 15
    raidhc3 = 16
    raidvc2 = 17
    raidvc3 = 18
    rlroleid = 19
    vethc1 = 20
    vetvc1 = 21
    vetroleid = 22
    vetrlroleid = 23
    creationmonths = 24
    subverify1id = 25
    subverify1name = 26
    subverify1roleid = 27
    subverifylogchannel = 28
    subverify2id = 29
    subverify2name = 30
    subverify2roleid = 31
    mmroleid = 32
    raidcommandschannel = 33
    vetcommandschannel = 34
    vethc2 = 35
    vetvc2 = 36
    eventrlid = 37
    eventcommandschannel = 38
    eventhc1 = 39
    eventvc1 = 40
    eventhc2 = 41
    eventvc2 = 42
    raiderroleid = 43
    leaderboardchannel = 44
    zerorunchannel = 45
    punishlogchannel = 46
    suspendedrole = 47
    securityrole = 48
    numpopsfirst = 49
    firstpopperrole = 50
    numpopssecond = 51
    secondpopperrole = 52
    numpopsthird = 53
    thirdpopperrole = 54
    firstpopperearlyloc = 55
    secondpopperearlyloc = 56
    thirdpopperearlyloc = 57
    rusherrole = 58
    maxrushersgetloc = 59
    modmailcategory = 60
    modmaillogchannel = 61
