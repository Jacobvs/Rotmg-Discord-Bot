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
    cursor.execute("SELECT * from guilds WHERE id = {})".format(uid))
    return cursor.fetchone()


def user_exists(uid):
    if get_user(uid) is None:
        return False
    return True


def add_new_user(user_id, guild_name, verify_id):
    sql = "INSERT INTO users (id, status, verifyguild, verifyid) VALUES (%s, %s, %s, %s)"
    data = (user_id, "stp_1", guild_name, verify_id)
    cursor.execute(sql, data)

    mydb.commit()


def update_user(id, column, change):
    if isinstance(change, str):
        change = "'{}'".format(change)
    sql = "UPDATE users SET {} = {} WHERE id = {}".format(column, change, id)
    print(sql)
    cursor.execute(sql)
    mydb.commit()
    print(cursor.rowcount)


class usr_cols(enum.Enum):
    id = 0  # Int
    ign = 1  # String
    status = 2  # String
    verifyguild = 3  # String
    verifykey = 4  # String
    verifyid = 5  # Int
    verifiedguilds = 6  # String (CSV)

class gld_cols(enum.Enum):
    id = 0  # Int
    name = 1  # String
    verificationid = 2  # Int
    nmaxed = 3  # Int
    nfame = 4  # Int
    reqboth = 5  # Boolean
    privateloc = 6  # Boolean
    reqsmsg = 7  # String (formatted)
