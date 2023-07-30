import postgreDB
import json
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.utils import get_random_id
from enum import Enum
from user import User

class Positions(Enum):
    """Перечисление возможных состояний пользователя"""
    REGISTER = 0
    SET_AGE = 1
    SET_GENDER = 2
    FIND_CITY = 3
    SET_CITY = 4
    SET_RELATION = 5
    AWAIT = 6

class VkinderBot():
    """Класс бота

    Содержит в себе методы для работы с API VK и логику работы бота

    """ 

    relations = [
        "не указано",
        "не женат/не замужем",
        "есть друг/есть подруга",
        "помолвлен/помолвлена",
        "женат/замужем",
        "всё сложно",
        "в активном поиске",
        "влюблён/влюблена",
        "в гражданском браке",
        ]
    
    def __init__(self, user_token, user_login, user_password, group_token, pg_link):
        """Инициализация объекта класса

        Входные параметры:
        user_token - Токен пользователя
        user_login - Логин пользователя
        user_password - Пароль пользователя
        group_token - Токен группы
        pg_link - URL подключения к базе данных postgreSQL

        """ 
        self.vk_user = vk_api.VkApi(token=user_token, login=user_login, password=user_password)
        self.vk_group = vk_api.VkApi(token=group_token)
        self.longpoll = VkLongPoll(self.vk_group)
        self.DB = postgreDB.PostgreDB(pg_link)
        
    def start(self):
        """Метод запуска бота. 
         
        В данном методе выполняется бесконечное прослушивание longpoll и обработка сообщений
        
        """ 
        for event in self.longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW:
                if event.to_me:
                    user_position = self.DB.get_user_position(event.user_id)
                    print(user_position, Positions.SET_AGE.value)
                    if user_position == Positions.REGISTER.value:
                        self.write_msg(event.user_id, "Добро пожаловать в Vkinder.")
                        user_info = self.__get_user_info(event.user_id)
                        self.DB.insert_users_table(user_info)
                        if user_info.age == None:
                            self.__goto_set_age(event.user_id)
                        elif user_info.gender == None:
                            self.__goto_set_gender(event.user_id)
                        elif user_info.cityId == None:
                            self.__goto_find_city(event.user_id)
                        elif user_info.relation == None:
                            self.__goto_set_relation(event.user_id)
                        else:
                            self.DB.update_user_position(event.user_id, Positions.AWAIT.value)    
                        del user_info
                    elif user_position == Positions.SET_AGE.value:
                        try:
                            age = int(event.text)
                            self.DB.update_user_age(event.user_id, age)
                            self.__goto_set_gender(event.user_id)  
                        except ValueError:
                            self.write_msg(event.user_id, "Ошибка ввода. Введите целое число.")
                    elif user_position == Positions.SET_GENDER.value:
                        if 'payload' in event.extra_values:
                            payload = json.loads(event.payload)
                            self.DB.update_user_gender(event.user_id, int(payload))
                        else:
                            self.__goto_set_gender(event.user_id) 
                            continue
                        self.__goto_find_city(event.user_id)
                    elif user_position == Positions.FIND_CITY.value:
                        cities = self.get_cities_by_search(event.text)
                        if cities["count"] == 0:
                            self.write_msg(event.user_id, "Город не найден")
                        else:
                            self.__goto_set_city(event.user_id, cities)    
                    elif user_position == Positions.SET_CITY.value:
                        if 'payload' in event.extra_values:
                            payload = json.loads(event.payload)
                            self.DB.update_user_city(event.user_id, int(payload))
                            self.__goto_set_relation(event.user_id)
                        else:
                            self.__goto_find_city(event.user_id)    
                    elif user_position == Positions.SET_RELATION.value:
                        if 'payload' in event.extra_values:
                            payload = json.loads(event.payload)
                            self.DB.update_user_relation(event.user_id, int(payload))
                            self.__search_users_by_params(event.user_id)
                        else:
                            self.__goto_set_relation(event.user_id)    
                    elif user_position == Positions.AWAIT.value:
                        if event.text == "Поиск":
                            pair_id = self.DB.get_pair_from_table(event.user_id)
                            if not pair_id:
                                self.write_msg(event.user_id, "Больше нет непоказанных пользователей. Требуется установить новые настройки")
                                self.__goto_set_age(event.user_id)
                                continue
                            pair_info = self.__get_user_info(pair_id)
                            profile_photos = self.__get_photos_by_user_id(pair_id)
                            profile_photos = profile_photos["items"]
                            profile_photos = sorted(profile_photos, 
                                                    key=lambda photo: photo.get("likes").get("count"))
                            attachments_list = []
                            for i in range(3):
                                photo = profile_photos.pop()
                                attachment_str = f"photo{pair_id}_{photo.get('id')}"
                                attachments_list.append(attachment_str)
                                if len(profile_photos) == 0:
                                    break
                            attachments_str = ",".join(attachments_list)     
                            message = f"@id{pair_id}({pair_info.firstname} {pair_info.lastname})\nВозраст: {pair_info.age}"
                            self.write_msg_with_attachments(event.user_id, message, attachments_str)
                        elif event.text == "Изменить настройки":   
                            self.DB.drop_pairs_from_table(event.user_id)
                            self.__goto_set_age(event.user_id)

    def get_cities_by_search(self, message):
        """Метод поиска городов.
         
        Для введенного пользователем названия выполняется запрос к API с целью получения списка городов
        
        """ 
        cities = self.vk_user.method('database.getCities', {'country_id':1,
                                                            'q': message,
                                                            'count':8})
        return cities
    
    def __get_photos_by_user_id(self, user_id):
        """Метод получения фотографий пользователя.
         
        Входные параметры:
        - user_id - ID пользователя
        
        """ 
        photos = self.vk_user.method('photos.get', {'owner_id': user_id,
                                                    'extended': True,
                                                    'album_id': 'profile'})
        return photos
    
    def write_msg(self, user_id, message):
        """Метод отправки сообщения пользователю
         
        Входные параметры:
        user_id - ID пользователя
        message - Отправляемое ообщение
        
        """ 
        keyboard = VkKeyboard()
        self.vk_group.method('messages.send', {'user_id': user_id, 
                                                'message': message,
                                                'random_id':get_random_id(),
                                                'keyboard': keyboard.get_empty_keyboard()})
            
    def write_msg_with_keyboard(self, user_id, message, keyboard):
        """Метод отправки сообщения с клавиатурой
         
        Входные параметры:
        user_id - ID пользователя
        message - Отправляемое ообщение
        keyboard - объект клавиатуры

        """ 
        self.vk_group.method('messages.send', {'user_id': user_id, 
                                                'message': message,
                                                'keyboard': keyboard.get_keyboard(), 
                                                'random_id': get_random_id()})

    def write_msg_with_attachments(self, user_id, message,  attachments):
        """Метод отправки сообщения с приложениями
         
        Входные параметры:
        user_id - ID пользователя
        message - Отправляемое ообщение
        attachments - строка приложений

        """ 
        self.vk_group.method('messages.send', {'user_id': user_id, 
                                                'message': message,
                                                'attachment': attachments, 
                                                'random_id': get_random_id()})

    def __goto_set_age(self, user_id):
        """Метод перехода пользователя в состояние установки возраста
         
        Входные параметры:
        user_id - ID пользователя

        """ 
        self.DB.update_user_position(user_id, Positions.SET_AGE.value)
        self.write_msg(user_id, "Укажите возраст:")

    def __goto_set_gender(self, user_id):
        """Метод перехода пользователя в состояние установки пола
         
        Входные параметры:
        user_id - ID пользователя

        """         
        self.DB.update_user_position(user_id, Positions.SET_GENDER.value)
        keyboard = VkKeyboard()
        keyboard.add_button(label="Мужской", payload=2)
        keyboard.add_button(label="Женский", payload=1)
        self.write_msg_with_keyboard(user_id, "Укажите пол:", keyboard)

    def __goto_find_city(self, user_id):
        """Метод перехода пользователя в состояние поиска города
         
        Входные параметры:
        user_id - ID пользователя

        """   
        self.DB.update_user_position(user_id, Positions.FIND_CITY.value)
        self.write_msg(user_id, "Укажите город:")

    def __goto_set_city(self, user_id, cities):
        """Метод перехода пользователя в состояние установки города
         
        Входные параметры:
        user_id - ID пользователя
        cities - данные о найденных городах

        """   
        self.DB.update_user_position(user_id, Positions.SET_CITY.value)
        cities = cities["items"]
        len_cities = len(cities) - 1
        keyboard = VkKeyboard()
        for idx, city in enumerate(cities):
            keyboard.add_button(label=city["title"], payload=city["id"])
            if idx % 2 == 0 and idx != len_cities:
                keyboard.add_line()
        self.write_msg_with_keyboard(user_id, "Выберите город:", keyboard)

    def __goto_set_relation(self, user_id):
        """Метод перехода пользователя в состояние установки семейного положения
         
        Входные параметры:
        user_id - ID пользователя

        """           
        self.DB.update_user_position(user_id, Positions.SET_RELATION.value)
        keyboard = VkKeyboard()
        for idx, relation in enumerate(self.relations):
            keyboard.add_button(label=relation, payload=idx)
            if idx % 3  == 0:
                keyboard.add_line()
        self.write_msg_with_keyboard(user_id, "Выберите семейное положение:", keyboard)

    def __search_users_by_params(self, user_id):
        """Метод поиска пользователей, соответствующих параметрам, заданных пользователем бота
         
        Входные параметры:
        user_id - ID пользователя

        """   
        user_info = self.DB.get_user_info(user_id)
        response = self.vk_user.method('users.search', {'city': int(user_info.cityId), 
                                                        'sex': int(user_info.gender),
                                                        'status': int(user_info.relation),
                                                        'age_from': user_info.age - 1,
                                                        'age_to': user_info.age + 1,
                                                        'has_photo' : True,
                                                        'count' : 1000}
                                                        )
        if response["count"] > 0:
            users = response["items"]
            not_closed_users = list(filter(lambda user: user["is_closed"] == False, users))
            users_ids = [user["id"] for user in not_closed_users]
            self.DB.insert_pairs_table(user_id, users_ids)
            self.__goto_await(user_id)
        else:
            self.write_msg(user_id, "Не найдены пользователи в соответствие с заданными настройками поиска.")
            self.__goto_set_age(user_id)

    def __goto_await(self, user_id):
        """Метод перехода пользователя в состояние поиска пар или перехода в меню настроек
         
        Входные параметры:
        user_id - ID пользователя

        """  
        self.DB.update_user_position(user_id, Positions.AWAIT.value)
        keyboard = VkKeyboard()
        keyboard.add_button("Поиск", VkKeyboardColor.POSITIVE.value)
        keyboard.add_line()
        keyboard.add_button("Изменить настройки", VkKeyboardColor.SECONDARY)
        self.write_msg_with_keyboard(user_id, "Выберите действие:", keyboard)

    def __get_user_info(self, user_id):
        """Метод получения информации о фамилии, имени, поле, городе, дате роджения и семейном положении пользователя
         
        Входные параметры:
        user_id - ID пользователя

        """  
        response = self.vk_user.method('users.get', {'user_ids': user_id, 
                                        'fields': 'sex, city, relation, bdate',
                                        'random_id': vk_api.u})[0]
        return User(response)
        
