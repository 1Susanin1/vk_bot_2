import psycopg2
from user import User
from random import shuffle 
class PostgreDB:
    def __init__(self, connection_string):
        """Конструктор объекта класса подключения к базе данных
        
        Входные параметры 
        connection_string - URL подключения к базе данных postgreSQL

        """
        self.connection = psycopg2.connect(connection_string)
        self.cursor = self.connection.cursor()

    def update_user_age(self, user_id, age):
        """Обновление возраста в таблице с данными о пользователе
        
        Входные параметры:
        user_id - ID пользователя
        age - возраст
        
        """
        self.cursor.execute(f""" UPDATE users SET age = {age} WHERE ID ={user_id};""")
        self.connection.commit()

    def update_user_gender(self, user_id, gender):
        """Обновление пола в таблице с данными о пользователе
         
        Входные параметры:
        user_id - ID пользователя
        gender - пол
        
        """
        self.cursor.execute(f""" UPDATE users SET gender = {gender} WHERE ID ={user_id};""")
        self.connection.commit()
    
    def update_user_city(self, user_id, cityId):
        """Обновление города в таблице с данными о пользователе
        
        Входные параметры:
        user_id - ID пользователя
        cityId - ID города
        
        """
        self.cursor.execute(f""" UPDATE users SET city_id = {cityId} WHERE ID ={user_id};""")
        self.connection.commit()

    def update_user_relation(self, user_id, relation):
        """Обновление семейного положения в таблице с данными о пользователе
        
        Входные параметры:
        user_id - ID пользователя
        relation - ID семейного положения

        """
        self.cursor.execute(f""" UPDATE users SET relation = {relation} WHERE ID ={user_id};""")
        self.connection.commit()

    def update_user_position(self, user_id, new_position):
        """Обновление состояния пользователя

        Входные параметры:
        user_id - ID пользователя
        new_position - номер состояния
        
        """
        self.cursor.execute(f"""UPDATE user_position SET positionId = {new_position} WHERE id = {user_id}""")
        self.connection.commit()  

    def get_user_position(self, user_id):
        """Загрузка состояния пользователя
        
        Входные параметры:
        user_id - ID пользователя

        Выходные параметры:
        position - номер состояния

        """
        self.cursor.execute(f"""SELECT positionId FROM user_position WHERE id = {user_id}""")
        results = self.cursor.fetchone()
        if results:
            return results[0]
        else:
            self.cursor.execute(f"""INSERT INTO user_position VALUES ({user_id}, 0);""")
            self.connection.commit()
            return 0
      
    def get_user_info(self, user_id):
        """Загрузка данных пользователя
        
        Входные параметры:
        user_id - ID пользователя

        Выходные параметры:
        user - Объект класса User, содержащий данные о пользователе

        """
        self.cursor.execute(f"""SELECT * FROM users WHERE id = {user_id}""")
        results = self.cursor.fetchone()
        user = User()
        user.id = results[0]
        user.firstname = results[1]
        user.lastname = results[2]
        user.age = results[3]
        user.gender = results[4]
        user.cityId = results[5]
        user.relation = results[6]
        return user
    
    def get_pair_from_table(self, user_id):
        """Выборка случайного id из таблицы с парами. Затем удаление данной пары из БД
        
        Входные параметры:
        user_id - ID пользователя

        Выходные параметры:
        pair_id -  ID предлагаемой пары 
 
        """
        self.cursor.execute(f"""SELECT pair_id FROM user_pairs WHERE id = {user_id}""")
        pair_id = self.cursor.fetchone()
        if pair_id:
            pair_id = pair_id[0]
            self.cursor.execute(F"""DELETE FROM user_pairs WHERE id = {user_id} AND pair_id = {pair_id}""")
            self.connection.commit()
            return pair_id
        else:
            return None
        
    def drop_pairs_from_table(self, user_id):
        """Удаленные пар для пользователя
        
        Входные параметры:
        user_id - ID пользователя

        """
        self.cursor.execute(F"""DELETE FROM user_pairs WHERE id = {user_id}""")
        self.connection.commit()

    def insert_users_table(self, user):
        """Добавление записи в таблицу с данными о пользователе
        
        Входные параметры:
        user - Объект класса User, содержащий данные о пользователе

        """
        self.cursor.execute(f"""
INSERT INTO users 
VALUES ({user.id}, '{user.firstname}', '{user.lastname}', 
{user.age if user.age else "null"}, 
{user.gender if user.gender else "null"}, 
{user.cityId if user.cityId else "null"}, 
{user.relation if user.relation else "null"});"""
        )
        self.connection.commit()
    
    def insert_pairs_table(self, user_id, pair_ids):
        """Добавление ID найденных людей в таблицу с парами
        
        Входные параметры:
        user_id - ID пользователя
        pair_ids -  ID добавляемых найденных пар
 
        """
        shuffle(pair_ids)
        pairs_str = [f"({user_id}, {pair_id})" for pair_id in pair_ids]
        pairs_str = ", ".join(pairs_str)
        self.cursor.execute("INSERT INTO user_pairs VALUES " + pairs_str)
        self.connection.commit()

    def create_users_table(self):
        """Создание таблицы с данными о пользователе"""
        self.cursor.execute("""
CREATE TABLE IF NOT EXISTS users(ID INT PRIMARY KEY,
firtname VARCHAR(255),
lastname VARCHAR(255),
age INT,
gender INT CHECK (gender IN(1, 2)),
city_id int,
relation INT CHECK (relation >= 0 and relation <=8)
);"""
        )
        self.connection.commit()
    
    def create_user_position_table(self):
        """Создание таблицы с данными о позиции пользователя в меню"""
        self.cursor.execute("""
CREATE TABLE IF NOT EXISTS user_position
( ID INT PRIMARY KEY,
positionId INT
);"""
    )
        
    def create_user_pairs_table(self):
        """Создание таблицы с данными о подходящих парах"""
        self.cursor.execute("""
CREATE TABLE IF NOT EXISTS user_pairs(
ID INT,
pair_id INT
);"""
    )
        self.connection.commit()

    def __del__(self):
        self.cursor.close()
        self.connection.close()
        
