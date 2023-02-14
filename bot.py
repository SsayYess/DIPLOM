from random import randrange
import requests
import datetime
import psycopg2
from database import create_db, clean_tbs, add_data, show_data, name_db, password_db
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

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
        response = requests.get(url, params={**self.params, **params})
        if response.status_code == 200:
            return response.json()['response']

    def get_photo(self, user_id: str, count):
        url = 'https://api.vk.com/method/photos.get'
        params = {
            'owner_id': user_id,
            'album_id': 'profile',
            'extended': 'likes',
            'photo_sizes': '1',
            'count': count
        }
        response = requests.get(url, params={**self.params, **params})
        if response.status_code == 200:
            return response.json()['response']['items']


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
            photo_grade.append((i['owner_id'], i['id'], i['likes']['count'] + i['comments']['count']))
        photo_grade = sorted(photo_grade, key=lambda likes: likes[-1], reverse=True)
        photos = ''
        for i in range(3):
            try:
                if i == 0:
                    photos += f'photo{photo_grade[i][0]}_{photo_grade[i][1]}'
                else:
                    photos += f',photo{photo_grade[i][0]}_{photo_grade[i][1]}'
            except IndexError:
                pass
        write_msg(user_id, f'https://vk.com/{self.screen_name}', photos)


def create_users_list(count):
    tmp_list = []
    for counter in range(count):
        tmp_list.append(randrange(10000000))
    return vk.users_info(','.join(map(str, tmp_list)))


def check_users(user_list, id_stop_list):
    tmp_list = []
    for user in user_list:
        try:
            Any = user['deactivated']
        except KeyError:
            if not (user['is_closed']) or (user['is_closed'] and user['can_access_closed']) and (user not in id_stop_list):
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
    return {'min_age': 20, 'max_age': 40, 'sex': 0, 'city': 'Москва', 'relation': 0}


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
    return list_of_param


def change_params(list_of_param, params):
    if len(params) != 5:
        write_msg(user_id, 'введены неверные данные')
    else:
        list_of_param['min_age'] = int(params[0])
        list_of_param['max_age'] = int(params[1])
        if list_of_param['min_age'] < 18:
            list_of_param['min_age'] = 18
        if list_of_param['max_age'] < 18:
            list_of_param['max_age'] = 25
        list_of_param['sex'] = int(params[2])
        if list_of_param['sex'] > 2 or list_of_param['sex'] < 0:
            list_of_param['sex'] = 0
        list_of_param['city'] = params[3].capitalize()
        if len(list_of_param['city']) < 2:
            list_of_param['city'] = 'Любой'
        list_of_param['relation'] = int(params[4])
        if list_of_param['relation'] > 8 or list_of_param['relation'] < 0:
            list_of_param['relation'] = 0
    return list_of_param


def search(count):
    with psycopg2.connect(database=name_db, user='postgres', password=password_db) as conn:
        id_from_base = show_data(conn)
        flag = True
        while flag:
            users = create_users_list(count)
            tmp_ml = check_users(users, id_from_base)
            print(len(tmp_ml))
            if len(tmp_ml) > 0:
                flag = False
    return tmp_ml


def show_result(tmp_ml):
    if len(tmp_ml) > 0:
        men = tmp_ml[0]
        print(user_id, men)
        write_msg(user_id, f'{men}')
        Candidate.get_info(men)
        with psycopg2.connect(database=name_db, user='postgres', password=password_db) as conn:
            add_data(conn, men.id)
        conn.close()
        tmp_ml.remove(men)
    else:
        tmp_ml = search(900)
        show_result(tmp_ml)
    return tmp_ml


def write_msg(user_id, message, photos=None):
    session.method('messages.send', {
        'user_id': user_id,
        'message': message,
        'random_id': randrange(10 ** 7),
        'attachment': photos
    })


vk = UsersVK(user_token, main_user_id)
session = vk_api.VkApi(token=bot_token)

with psycopg2.connect(database=name_db, user='postgres', password=password_db) as conn:
    create_db(conn)
    clean_tbs(conn)
    create_db(conn)
conn.close()

list_of_param = ini_lop()
for event in VkLongPoll(session).listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        user_request = event.text.lower()
        user_id = event.user_id
        main_user = Candidate(vk.users_info(user_id)[0])

        if user_request == 'привет':
            list_of_param = check_lop(list_of_param, main_user)
            write_msg(user_id, f'Привет, {main_user.name} \n '
                               f'Список команд по запросу help')

        if user_request == 'параметры':
            write_msg(user_id, f'Похоже вы ищете: {sex_list[list_of_param["sex"]]} от {list_of_param["min_age"]} до {list_of_param["max_age"]} {age_list[list_of_param["max_age"] % 10]} из города {list_of_param["city"]} статус отношений - {relation_status[list_of_param["relation"]]}\n'
                               f'для изменения параметров введи: ИЗМЕНИТЬ и параметры через запятую: \n'
                               f'ВОЗРАСТ от, до, ПОЛ (1 для поиска женщины, 2 для поиска мужчины, 3 для поиска без учета пола), ГОРОД, '
                               f'СТАТУС ОТНОШЕНИЙ (1 - не женат / не замужем, 2 - есть друг / есть подруга, 3 - помолвлен / помолвлена, '
                               f'4 - женат / замужем, 5 - всё сложно, 6 - в активном поиске, 7 - влюблён / влюблена, 8 - в гражданском браке, '
                               f'0 - интеллектуальный поиск)\n'
                               f'пример запроса\nИЗМЕНИТЬ 20,35,2,Москва,0')

        if user_request.split(' ')[0] == 'изменить':
            params = user_request.split(" ")[1].strip().split(',')
            list_of_param = change_params(list_of_param, params)
            write_msg(user_id, f'Ищем {sex_list[list_of_param["sex"]]} от {list_of_param["min_age"]} до {list_of_param["max_age"]} '
                                   f'{age_list[list_of_param["max_age"] % 10]} из города {list_of_param["city"]} статус отношений - {relation_status[list_of_param["relation"]]}')

        if user_request in ['help', 'помощь', 'команды']:
            write_msg(user_id, f'параметры - покажу заданные параметры поиска\n'
                               f'изменить - изменим параметры поиска\n'
                               f'поиск - найду для вас подходящих кандидатов\n')

        if user_request == 'поиск':
            man_list = search(900)
            man_list = show_result(man_list)

        if user_request == 'далее':
            man_list = show_result(man_list)

        if user_request == 'стоп':
            break
