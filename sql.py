import enum

import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

mydb = mysql.connector.connect(
    host="localhost",
    user="root",
    passwd=os.getenv("MYSQL_PASSWORD"),
    auth_plugin='mysql_native_password',
    database="rotmg"
)

cursor = mydb.cursor()


def get_user(uid):
    cursor.execute("SELECT * from users WHERE id = {}".format(uid))
    return cursor.fetchone()


def get_guild(uid):
    cursor.execute("SELECT * from guilds WHERE id = {}".format(uid))
    return cursor.fetchone()


def user_exists(uid):
    if get_user(uid) is None:
        return False
    return True


def add_new_user(user_id, guild_id, verify_id):
    sql = "INSERT INTO users (id, status, verifyguild, verifyid) VALUES (%s, 'stp_1', %s, %s)"
    data = (user_id, guild_id, verify_id)
    cursor.execute(sql, data)
    mydb.commit()


def update_user(id, column, change):
    # if isinstance(change, str):
    #     change = "'{}'".format(change)
    sql = "UPDATE users SET {} = %s WHERE id = {}".format(column, id)
    cursor.execute(sql, (change,))
    mydb.commit()


def add_new_guild(guild_id, guild_name):
    sql = "INSERT INTO guilds (id, name, verificationid, nmaxed, nfame, reqboth, privateloc, reqsmsg, verifiedroleid) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
    data = (guild_id, guild_name, 0, 0, 0, False, True, "", 0)
    cursor.execute(sql, data)
    mydb.commit()


def update_guild(id, column, change):
    # if isinstance(change, str):
    #     change = "'{}'".format(change)
    sql = "UPDATE guilds SET {} = %s WHERE id = {}".format(column, id)
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
    reqboth = 5  # Boolean
    privateloc = 6  # Boolean
    reqsmsg = 7  # String (formatted)
    manualverifychannel = 8  # Int
    verifiedroleid = 9  # Int
