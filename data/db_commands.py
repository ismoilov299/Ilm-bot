import sqlite3
import datetime


class DataBase:
    def __init__(self, path_to_db ='backend/ilmbot/db.sqlite3'):
        self.path_to_db = path_to_db

    @property
    def connection(self):
        return sqlite3.connect(self.path_to_db)

    def execute(self, sql: str, parameters: tuple = None, fetchone=False, fetchall=False, commit=False):
        if not parameters:
            parameters = ()
        connection = self.connection
        connection.set_trace_callback(logger)
        cursor = connection.cursor()
        data = None
        cursor.execute(sql, parameters)

        if commit:
            connection.commit()
        if fetchall:
            data = cursor.fetchall()
        if fetchone:
            data = cursor.fetchone()
        connection.close()
        return data

#     def create_table_users(self):
#         sql = """
#         CREATE TABLE IF NOT EXISTS bot_namazuser (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             user_id int NOT NULL UNIQUE,
#             name varchar(255) NOT NULL,
#             region varchar(255) NULL,
#             subscribe int DEFAULT 0
#             );
# """
#         self.execute(sql, commit=True)

    def add_user(self, user_id: int, user_name: str, region: str = None, subscribe: int = 0):
        sql = """
        INSERT INTO bot_namazuser(user_id, user_name, region, subscribe) VALUES (?, ?, ?, ?)
        """
        self.execute(sql, parameters=(user_id, user_name, region, subscribe), commit=True)

    def select_user(self,region: str, subscribe: int, user_id: int):
        return self.execute("SELECT * FROM bot_namazuser WHERE region=? and subscribe=? and user_id=?", parameters=(region, subscribe, user_id), fetchone=True)

    def get_users_subscribe(self):
        return self.execute("SELECT * FROM bot_namazuser WHERE subscribe=1",fetchall=True)

    def get_times(self):
        return self.execute("SELECT Mintaqa,Bomdod,Quyosh,Peshin,Asr,Shom,Xufton FROM namaz WHERE Sana=?",(datetime.datetime.now().strftime('%d.%m.%Y'),),fetchall=True)

    def get_bugun(self,mintaqa:str):
        delta = datetime.timedelta(hours=5)
        return self.execute("SELECT * FROM namaz WHERE Sana=? AND Mintaqa=?",((datetime.datetime.now()+delta).strftime('%d.%m.%Y'),mintaqa),fetchall=True)

    def update_user(self, region: str, subscribe: int, user_id: int):
        self.execute("UPDATE bot_namazuser SET region=?, subscribe=? WHERE user_id=?", parameters=(region, subscribe, user_id), commit=True)



    def select_all_users(self):
        return self.execute("SELECT seq FROM sqlite_sequence",fetchone=True)

    def select_all_users2(self):
        return self.execute("SELECT user_id FROM bot_namazuser",fetchall=True)

    def select_one(self):
        return self.execute("SELECT user_id, name FROM bot_namazuser",fetchall=True)

    def count_obuna(self):
        return self.execute("SELECT user_id,name,region FROM bot_namazuser WHERE subscribe=1", fetchall=True)

def logger(statement):
    print(f"""
--------------------------------------------------------
Executing:
 {statement}
--------------------------------------------------------
""")







