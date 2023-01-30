import random
from random import randrange
import time
from time import sleep
import requests
import datetime
import psycopg2
from database import create_db, clean_tbs, add_data, show_data, name_db, password_db

with open('bot_token.txt', 'r') as file:
    bot_token = file.readline().strip()
with open('user_token.txt', 'r') as file:
    user_token = file.readline().strip()
    main_user_id = file.readline().strip()

class UsersVK:

    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {
            'access_token': self.token,
            'v': self.version
        }

    def users_info(self, user_id):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': user_id, 'fields': 'sex, city, bdate, screen_name, counters, relation'}
        response = requests.get(url, params={**self.params, **params}).json()
        return response['response']

    def get_photo(self, user_id: str, count):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 'likes',
            'photo_sizes': '1',
            'count': count
        }
        response = requests.get(url, params={**self.params, **params}).json()
        return response['response']['items']


class Candidate():

    def __init__(self, user_id):
        self.id = user_id['id']
        self.name = user_id['first_name']
        self.surname = user_id['last_name']
        try:
            day, month, year = user_id['bdate'].split('.')
            bdate_user = datetime.date(int(year), int(month), int(day))
            self.age = int((datetime.date.today() - bdate_user).days / 365.25)
        except KeyError:
            self.age = 0
        except ValueError:
            self.age = 0
        self.sex = user_id['sex']
        try:
            self.city = user_id['city']['title']
        except KeyError:
            self.city = None
        try:
            self.relation = int(user_id['relation'])
        except KeyError:
            self.relation = 0
        self.photos = 0
        self.screen_name = user_id['screen_name']
        self.grade = self.set_grade()

    def set_grade(self):
        global list_of_param
        age_min = list_of_param['min_age']
        age_max = list_of_param['max_age']
        sex = list_of_param['sex']
        city = list_of_param['city']
        relation = list_of_param['relation']
        grade_cand = 0
        if age_min < self.age < age_max:
            grade_cand += 10
        if relation == 0:
            if self.relation == 4 or self.relation == 3 or self.relation == 8:
                grade_cand -= 10
            elif self.relation == 2 or self.relation == 7 or self.relation == 0:
                grade_cand += 2
            else:
                grade_cand += 12
        else:
            if self.relation == relation:
                grade_cand += 12
        if self.city == city or city == 'Любой':
            grade_cand += 20
        if sex != 0 and self.sex != sex:
            grade_cand = 0
        return grade_cand

    def __str__(self):
        relation_status = ['не указан', 'не женат / не замужем', 'есть друг / есть подруга', 'помолвлен / помолвлена',
                           'женат / замужем', 'всё сложно', 'в активном поиске', 'влюблён / влюблена',
                           'в гражданском браке']
        age_name = ['лет', 'год', 'года', 'года', 'года', 'лет', 'лет', 'лет', 'лет', 'лет']
        if self.age == 0:
            return f'{self.name}, возраст не указан, статус отношений: {relation_status[self.relation]}, рейтинг: {self.grade}, {self.city}'
        else:
            return f'{self.name}, {self.age} {age_name[self.age % 10]}, статус отношений: {relation_status[self.relation]}, рейтинг: {self.grade}, {self.city}'

    def get_info(self):
        photo_user = vk.get_photo(self.id, 100)
        photo_grade = []
        for i in photo_user:
            photo_grade.append((i['sizes'][-1]['url'], i['likes']['count'] + i['comments']['count']))
        photo_grade = sorted(photo_grade, key=lambda likes: likes[-1], reverse=True)
        for i in range(3):
            try:
                print(photo_grade[i][0])
            except IndexError:
                pass
        print('https://vk.com/'+self.screen_name)


def create_users_list(count):
    tmp_list = []
    for counter in range(count):
        tmp_list.append(randrange(10000000))
    return vk.users_info(','.join(map(str, tmp_list)))


def check_users(user_list):
    tmp_list = []
    for user in user_list:
        try:
            Any = user['deactivated']
        except KeyError:
            if not (user['is_closed']) or (user['is_closed'] and user['can_access_closed']):
                man = Candidate(user)
                if man.grade > 22:
                    tmp_list.append(man)
    return sorted(tmp_list, key=lambda candidate: candidate.grade, reverse=True)


def ini_lop():
    global sex_list
    sex_list = ['человека', 'женщину', 'мужчину']
    global age_list
    age_list = ['лет', 'года', 'лет', 'лет', 'лет', 'лет', 'лет', 'лет', 'лет', 'лет']
    global relation_status
    relation_status = ['не указан', 'не женат / не замужем', 'есть друг / есть подруга',
                       'помолвлен / помолвлена',
                       'женат / замужем', 'всё сложно', 'в активном поиске', 'влюблён / влюблена',
                       'в гражданском браке']
    return {'min_age': 18, 'max_age': 40, 'sex': 0, 'city': 'Любой', 'relation': 0}


def check_lop(list_of_param, main_user):
    if main_user.age != 0:
        list_of_param['min_age'] = main_user.age - 5
        list_of_param['max_age'] = main_user.age + 10
    if main_user.city:
        list_of_param['city'] = main_user.city
    if main_user.sex == 1:
        list_of_param['sex'] = 2
    elif main_user.sex == 2:
        list_of_param['sex'] = 1
    print(
        f'Похоже вы ищете: незамужнего(-юю) {sex_list[list_of_param["sex"]]} от {list_of_param["min_age"]} до {list_of_param["max_age"]} {age_list[list_of_param["max_age"] % 10]} из города {list_of_param["city"]}')
    return list_of_param

def change_lop(list_of_param):
    while True:
        user_input = input('Хотите изменить критерии поиска? ').strip()
        if user_input.lower() in ['y', 'yes', 'да', 'д', 'хочу']:
            while True:
                user_input_2 = input('Что хотите изменить? пол, возраст, город, семейное положение? ').strip()
                if user_input_2.lower() == 'пол':
                    list_of_param['sex'] = int(input(
                        'Введите 1 для поиска женщины, 2 для поиска мужчины, 3 для поиска без учета пола ').strip())
                elif user_input_2.lower() == 'возраст':
                    user_input_list = input('Введите возраст через дефиз ').split('-')
                    list_of_param['min_age'] = int(user_input_list[0])
                    list_of_param['max_age'] = int(user_input_list[1])
                    if list_of_param['min_age'] < 18:
                        list_of_param['min_age'] = 18
                    if list_of_param['max_age'] < 18:
                        list_of_param['max_age'] = 18
                elif user_input_2.lower() == 'город':
                    list_of_param['city'] = input('Введите город (любой - для поиска без учета города) ').strip().capitalize()
                elif user_input_2.lower() == 'семейное положение':
                    list_of_param['relation'] = int(
                        input(
                            'Введите 1 - не женат / не замужем, 2 - есть друг / есть подруга, 3 - помолвлен / помолвлена,'
                            '4 - женат / замужем, 5 - всё сложно, 6 - в активном поиске, 7 - влюблён / влюблена, '
                            '8 - в гражданском браке, 0 - интеллектуальный поиск ').strip())
                elif user_input_2.lower() in ['q', 'ничего']:
                    return list_of_param
        elif user_input.lower() in ['n', 'no', 'нет', 'н']:
            print(f'Ищем {sex_list[list_of_param["sex"]]} от {list_of_param["min_age"]} до {list_of_param["max_age"]} {age_list[list_of_param["max_age"] % 10]} из города {list_of_param["city"]} статус отношений - {relation_status[list_of_param["relation"]]}')
            return list_of_param



def add_and_show_candidats(user_list, base_list):
    tmp_list = []
    for men in user_list:
        if men.id not in base_list:
            print(men)
            Candidate.get_info(men)
            sleep(0.5)
            tmp_list.append(men.id)
    return tmp_list


vk = UsersVK(user_token, main_user_id)

list_of_param = ini_lop()
main_user = Candidate(vk.users_info(main_user_id)[0])
print('Привет,', main_user.name)

list_of_param = check_lop(list_of_param, main_user)
list_of_param = change_lop(list_of_param)

with psycopg2.connect(database=name_db, user='postgres', password=password_db) as conn:
    create_db(conn)
    a = True
    while a == True:
        users = create_users_list(300)
        man_list = check_users(users)
        id_from_base = show_data(conn)
        new_ids = add_and_show_candidats(man_list, id_from_base)
        if len(new_ids) != 0:
            for id_count in new_ids:
                add_data(conn, id_count)
            user_input = input('Новый поиск? ')
            if user_input.lower() in ['y', 'yes', 'да', 'д', 'хочу']:
                list_of_param = change_lop(list_of_param)
            else:
                print('До скорых встреч!')
                a = False

    # clean_tbs(conn)
    # create_db(conn)
conn.close()