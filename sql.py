import enum
import os
import main
import aiomysql
from dotenv import load_dotenv

load_dotenv()
bot = main.bot


@bot.event
async def on_ready():
    bot.pool = await aiomysql.create_pool(
        host=os.getenv("MYSQL_HOST"),
        port=3306,
        user='root',
        password=os.getenv("MYSQL_PASSWORD"),
        db='mysql',
        loop=bot.loop
    )

async def get_user(uid):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.users WHERE id = {}".format(uid))
            return cursor.fetchone()

async def get_num_verified():
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT COUNT(*) FROM rotmg.users where status = 'verified'")
            return cursor.fetchone()

async def get_guild(uid):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.guilds WHERE id = {}".format(uid))
            return cursor.fetchone()

async def ign_exists(ign, id):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * from rotmg.users WHERE ign = '{}' AND status = 'verified'".format(ign))
            user = cursor.fetchone()
            if not user:
                return False
            if user[0] == id:
                return False
            return True

# async def user_exists(uid):
#     if await get_user(uid) is None:
#         return False
#     return True


async def add_new_user(user_id, guild_id, verify_id):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "INSERT INTO rotmg.users (id, status, verifyguild, verifyid) VALUES (%s, 'stp_1', %s, %s)"
            data = (user_id, guild_id, verify_id)
            await cursor.execute(sql, data)
            await conn.commit()


async def update_user(id, column, change):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "UPDATE rotmg.users SET {} = %s WHERE id = {}".format(column, id)
            await cursor.execute(sql, (change,))
            await conn.commit()


async def add_new_guild(guild_id, guild_name):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = ("INSERT INTO rotmg.guilds (id, name, verificationid, nmaxed, nfame,"
                   "nstars, reqall, privateloc, reqsmsg, manualverifychannel, verifiedroleid,"
                   "verifylogchannel) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)")
            data = (guild_id, guild_name, 0, 0, 0, 0, False, True, "", 0, 0, 0)
            await cursor.execute(sql, data)
            # sql = (f"create table guild_tables.`{guild_id}_logs` (id int null, runcomplete int default"
            #        " 0 null, keypop int default 0 null, runled int default 0 null, eventcomplete int"
            #        " default 0 null, eventled int default 0 null, constraint"
            #        f" `{guild_id}_logs_pk` primary key (id));")
            # cursor.execute(sql)
            # sql = (f"create table `{guild_id}_punishments`(id int not null, type VARCHAR(255) null,"
            #        " expiry DATETIME null, reason VARCHAR(255) null, requester int null, "
            #        f"constraint `{guild_id}_punishments_pk` primary key (id));")
            # cursor.execute(sql)
            await conn.commit()


async def update_guild(id, column, change):
    async with bot.pool.acquire() as conn:
        async with conn.cursor() as cursor:
            sql = "UPDATE rotmg.guilds SET {} = %s WHERE id = {}".format(column, id)
            await cursor.execute(sql, (change,))
            await conn.commit()


class usr_cols(enum.IntEnum):
    id = 0  # Int
    ign = 1  # String
    status = 2  # String
    verifyguild = 3  # Int
    verifykey = 4  # String
    verifyid = 5  # Int
    verifiedguilds = 6  # String (CSV)


class gld_cols(enum.IntEnum):
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
    vethcid = 20
    vetvcid = 21
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
