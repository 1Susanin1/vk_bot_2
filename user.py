import datetime

class User:
    "Класс User, содержащий данные о пользователе"

    def __init__(self, data=dict()):
        """Инициализатор класса
        
        Входные параметры:
        data - Данные о пользователе в JSON, полученные по запросу от API

        """
        self.id        = data.get('id')
        self.firstname = data.get('first_name')
        self.lastname  = data.get('last_name')
        self.cityId    = data.get('city').get('id') if data.get('city') else None
        self.gender    = data.get('sex')
        self.relation  = data.get('relation')
        birthday       = data.get('bdate')
        self.age = self.get_age(birthday) if birthday else None

    def get_age(self, date):
        """Вычисление возраста
        
        Входные параметры:
        date - Дата рождения пользователя

        """
        birthday = datetime.datetime.strptime(date,'%d.%m.%Y')
        now = datetime.datetime.now()
        difference = now - birthday
        return int(difference.days/365.25)
    