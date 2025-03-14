import sqlite3

import hike
import threading

DB_FILE_NAME = 'sessions.db'
user0 = 'user123'
password0 = 'password123'

DB_SESSION_TABLE = {
    "name": "sessions",
    "cols": [
        "session_id text PRIMARY KEY",
        "km float",
        "steps integer",
        "burnt_kcal float",
        "session_user text",
    ]
}

DB_PASSWORD_TABLE = {
    "name": "passwords",
    "cols": [
        "username text PRIMARY KEY",
        "password text",
    ]
}


# lock object so multithreaded use of the same
# HubDatabase object 

class HubDatabase:
    """Hiking sesssion database interface class.

    An object of this class enables easy retreival and management of the
    hiking database content. If the database does not exist, the instantiation
    of this class will create the database inside `DB_FILE_NAME` file.
    
    Arguments:
        lock: lock object so multithreaded use of the same HubDatabase object
              is safe. sqlite3 does not allow the same cursor object to be
              used concurrently.
        con: sqlite3 connection object
        cur: sqlite3 cursor object
    """

    lock = threading.Lock()

    def __init__(self):
        self.con = sqlite3.connect(DB_FILE_NAME, check_same_thread=False)
        self.cur = self.con.cursor()

        for t in [DB_SESSION_TABLE]:
            create_table_sql = f"create table if not exists {t['name']} ({', '.join(t['cols'])})"
            self.cur.execute(create_table_sql)
            
        for t in [DB_PASSWORD_TABLE]:
            create_table_sql = f"create table if not exists {t['name']} ({', '.join(t['cols'])})"
            self.cur.execute(create_table_sql)

        self.con.commit()
        
    def init_user(self):
        try:
            self.lock.acquire()
            try:
                self.cur.execute(f"INSERT INTO {DB_PASSWORD_TABLE['name']} VALUES ('{user0}','{password0}')")
            except sqlite3.IntegrityError:
                print("WARNING: User info already exists in database!")
            self.con.commit()
        finally:
            self.lock.release()
            
    def save(self, s: hike.HikeSession, user):
        try:
            self.lock.acquire()

            try:
                self.cur.execute(f"INSERT INTO {DB_SESSION_TABLE['name']} VALUES ('{s.id}', {s.km}, {s.steps}, {s.kcal}, '{user}')")
            except sqlite3.IntegrityError:
                print("WARNING: Session ID already exists in database! Aborting saving current session.")

            self.con.commit()
        finally:
            self.lock.release()

    def get_sessions(self, user_id:str) -> list[hike.HikeSession]:
        try:
            self.lock.acquire()
            rows = self.cur.execute(f"SELECT * FROM {DB_SESSION_TABLE['name']} WHERE session_user='{user_id}'").fetchall()
        finally:
            self.lock.release()

        return list(map(lambda r: hike.from_list(r), rows))

        
    def login_check(self, user: str, pwd) -> bool:
        try:
            self.lock.acquire()
            rows = self.cur.execute(f"SELECT * FROM {DB_PASSWORD_TABLE['name']} WHERE username = '{user}' AND password = '{pwd}'").fetchall()
        finally:
            self.lock.release()

        if len(rows)!= 0:
            return True
        else:
            return False


    def __del__(self):
        self.cur.close()
        self.con.close()
