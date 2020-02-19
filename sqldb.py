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




# def get_cursor():
#   return cursor
#
#


def get_user(uid):
  cursor.execute("SELECT * from users WHERE id = {})".format(uid))
  return cursor.fetchone()


def add_new_user(user_id, guild_name, verify_id):
  sql = "INSERT INTO users (id, status, verifyguild, verifyid) VALUES (%s, %s, %s, %s)"
  data = (user_id, "stp_1", guild_name, verify_id)
  cursor.execute(sql, data)

  mydb.commit()

