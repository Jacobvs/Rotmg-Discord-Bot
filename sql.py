import enum

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

mydb = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST"),
    user="root",
    passwd=os.getenv("MYSQL_PASSWORD"),
    auth_plugin='mysql_native_password',
)

cursor = mydb.cursor()


def get_user(uid):
    cursor.execute("SELECT * from rotmg.users WHERE id = {}".format(uid))
    return cursor.fetchone()


def get_guild(uid):
    cursor.execute("SELECT * from rotmg.guilds WHERE id = {}".format(uid))
    return cursor.fetchone()


def user_exists(uid):
    if get_user(uid) is None:
        return False
    return True


def add_new_user(user_id, guild_id, verify_id):
    sql = "INSERT INTO rotmg.users (id, status, verifyguild, verifyid) VALUES (%s, 'stp_1', %s, %s)"
    data = (user_id, guild_id, verify_id)
    cursor.execute(sql, data)
    mydb.commit()


def update_user(id, column, change):
    # if isinstance(change, str):
    #     change = "'{}'".format(change)
    sql = "UPDATE rotmg.users SET {} = %s WHERE id = {}".format(column, id)
    cursor.execute(sql, (change,))
    mydb.commit()


def add_new_guild(guild_id, guild_name):
    sql = "INSERT INTO rotmg.guilds (id, name, verificationid, nmaxed, nfame, nstars, reqall, privateloc, reqsmsg, manualverifychannel, verifiedroleid, verifylogchannel) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = (guild_id, guild_name, 0, 0, 0, 0, False, True, "", 0, 0, 0)
    cursor.execute(sql, data)
    mydb.commit()


def update_guild(id, column, change):
    # if isinstance(change, str):
    #     change = "'{}'".format(change)
    sql = "UPDATE rotmg.guilds SET {} = %s WHERE id = {}".format(column, id)
    cursor.execute(sql, (change,))
    mydb.commit()


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
