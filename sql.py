import enum
from datetime import datetime, timedelta


async def get_user(pool, uid):
    """Return user data from rotmg.users table"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.users WHERE id = {}".format(uid))
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


# async def user_exists(uid):
#     if await get_user(uid) is None:
#         return False
#     return True


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


async def update_guild(pool, id, column, change):
    """Update guild data in rotmg.guilds"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "UPDATE rotmg.guilds SET {} = %s WHERE id = {}".format(column, id)
            await cursor.execute(sql, (change,))
            await conn.commit()

async def get_guild(pool, uid):
    """Return guild data from rotmg.guilds"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.guilds WHERE id = {}".format(uid))
            data = await cursor.fetchone()
            await conn.commit()
            return data

async def get_all_guilds(pool):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.guilds")
            data = await cursor.fetchall()
            await conn.commit()
            return data


async def construct_guild_database(pool, client):
    guilds = await get_all_guilds(pool)
    guild_db = {}
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
            await cursor.execute(f"SELECT * from rotmg.`{guild_id}` WHERE id = {member_id}")
            data = await cursor.fetchone()
            await conn.commit()
            if not data:
                await cursor.execute(f"INSERT INTO rotmg.`{guild_id}`(id) VALUES({member_id})")
                await conn.commit()

            name = "pkey" if column == 1 else "vials" if column == 2 else "helmrunes" if column == 3 else "shieldrunes" if column == 4 else\
                "swordrunes" if column == 5 else "eventkeys" if column == 6 else "runsdone" if column == 7 else "eventsdone" if column == 8\
                else "srunled" if column == 9 else "frunled" if column == 10 else "eventled" if column == 11 else "runsassisted" if\
                column == 12 else "eventsassisted"
            await cursor.execute(f"UPDATE rotmg.`{guild_id}` SET {name} = {name} + {number} WHERE id = {member_id}")
            await conn.commit()

async def get_log(pool, guild_id, member_id):
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(f"SELECT * from rotmg.`{guild_id}` WHERE id = {member_id}")
            data = await cursor.fetchone()
            await conn.commit()
            if not data:
                await cursor.execute(f"INSERT INTO rotmg.`{guild_id}`(id) VALUES({member_id})")
                await conn.commit()
                await cursor.execute(f"SELECT * from rotmg.`{guild_id}` WHERE id = {member_id}")
                data = await cursor.fetchone()
            return data

class log_cols(enum.IntEnum):
    id = 0
    pkey = 1
    vials = 2
    helmrunes = 3
    shieldrunes = 4
    swordrunes = 5
    eventkeys = 6
    runsdone = 7
    eventsdone = 8
    srunled = 9
    frunled = 10
    eventled = 11
    runsassisted = 12
    eventsassisted = 13
    weeklyruns = 14

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


gdb_channels = [9, 11, 13, 14, 15, 16, 17, 18, 20, 21, 28, 33, 34, 35, 36, 38, 39, 40, 41, 42]
gdb_roles = [10, 19, 22, 23, 27, 31, 32, 37, 43]
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


## EVENTS:
# CREATE EVENT `zero_runs_weekly`
#     ON SCHEDULE
#         EVERY 168 HOUR STARTS '2020-06-01 20:00:00'
#     ON COMPLETION PRESERVE
#     ENABLE
# DO BEGIN
#          UPDATE rotmg.`660344559074541579` SET weeklyruns = 0 WHERE weeklyruns <> 0;
#          UPDATE rotmg.`678528908429361152` SET weeklyruns = 0 WHERE weeklyruns <> 0;
#          UPDATE rotmg.`703987028567523468` SET weeklyruns = 0 WHERE weeklyruns <> 0;
#          UPDATE rotmg.`713655609760940044` SET weeklyruns = 0 WHERE weeklyruns <> 0;
#          UPDATE rotmg.`660344559074541579` SET weeklyassists = 0 WHERE weeklyassists <> 0;
#          UPDATE rotmg.`678528908429361152` SET weeklyassists = 0 WHERE weeklyassists <> 0;
#          UPDATE rotmg.`703987028567523468` SET weeklyassists = 0 WHERE weeklyassists <> 0;
#          UPDATE rotmg.`713655609760940044` SET weeklyassists = 0 WHERE weeklyassists <> 0;
# END