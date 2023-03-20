from BD_Vkinder import create_tables, engine, sessiondb, Options

from random import randrange

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api import VkUpload
import datetime

from vk_api.keyboard import VkKeyboard, VkKeyboardColor

keyboard_main = VkKeyboard(one_time=True)

keyboard_main.add_button('ДАЛЬШЕ', color=VkKeyboardColor.PRIMARY)
keyboard_main.add_line()
keyboard_main.add_button('Добавить в избранное', color=VkKeyboardColor.POSITIVE)
keyboard_main.add_button('Мое избранное', color=VkKeyboardColor.PRIMARY)
keyboard_main.add_button('Пока', color=VkKeyboardColor.NEGATIVE)

keyboard_start = VkKeyboard(one_time=True)
keyboard_start.add_button('Старт', color=VkKeyboardColor.PRIMARY)
keyboard_start.add_button('Пока', color=VkKeyboardColor.PRIMARY)

keyboard_forward = VkKeyboard(one_time=True)
keyboard_forward.add_button('ДАЛЬШЕ', color=VkKeyboardColor.PRIMARY)


def get_token(file):
    with open(file, "r") as file_object:
        token = file_object.readline().strip()
    return token


bot_token = get_token('bot_token.txt.')
vk_token = get_token('vk_token.txt.')


session = vk_api.VkApi(token=bot_token)
upload = VkUpload(session)
session_vk = vk_api.VkApi(token=vk_token)


def get_age(date):
    age = datetime.datetime.now().year-int(date[-4:])
    return age


def get_user_info(user_id):
    user_info = {}
    response = session.method('users.get', {
        'user_id': user_id,
        'v': 5.131,
        'fields': 'first_name, last_name, bdate, sex, city, country'
    })
    try:
        for key, value in response[0].items():
            if key == 'city':
                user_info[key] = value['id']
            elif key == 'bdate' and len(value.split('.')) == 3:
                user_info['age'] = get_age(value)
            else:
                user_info[key] = value
        return user_info
    except KeyError:
        write_msg(user_id, 'Ошибка')
        return False


def check_info(user_info):
    nes_list = ['age', 'city']
    missing_list = []
    for item in nes_list:
        if item not in user_info:
            missing_list.append(item)
    return missing_list


def add_bdate(user_id):
    a = False
    while a == False:
        write_msg(user_id, 'Недостаточно информации, введите ДАТУ РОЖДЕНИЯ в формате ДД.ММ.ГГГГ')
        for event in VkLongPoll(session).listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                if len(event.text.split('.')) == 3:
                    user_info['age'] = get_age(event.text)
                    a = True
                    return user_info
                else:
                    write_msg(user_id, 'Дата указана неверно, введите ДАТУ РОЖДЕНИЯ в формате ДД.ММ.ГГГГ')


def add_city(user_id):
    a = False
    while a is False:
        write_msg(user_id, 'Недостаточно информации, введите город в Именительном падеже')
        for event in VkLongPoll(session).listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me:
                response = session_vk.method('database.getCities', {
                    'country_id': 1,
                    'q': event.text,
                    'need_all': 0,
                    'count': 1
                })
                try:
                    if response['count'] == 0:
                        write_msg(user_id, 'Город указан неверно, введите город в именительном падеже')
                    else:
                        user_info['city'] = response['items'][0]['id']
                        a = True
                        return user_info

                except KeyError:
                    return None


def serch_users(user_info):
    response = session_vk.method('users.search', {
        'age_from': user_info['age']-3,
        'age_to': user_info['age']+3,
        'sort': 0,
        'count': 100,
        'city': user_info['city'],
        'sex': 3 - user_info['sex'],
        'status': 6,
        'has_photo': 1})

    list_users_id = []
    try:
        if len(response['items']) != 0:
            for item in response['items']:
                if item['is_closed'] is False:
                    list_users_id.append(item['id'])
        return list_users_id
    except KeyError:
        return None


def check_id(list_users_id):
    list_appeared_id = []     # список из базы данных
    new_list_users_id = []     # новый список без старых ай ди
    if sessiondb.query(Options).count() > 0:
        q = sessiondb.query(Options.option_id).filter(Options.user_id == user_id)
        for s in q.all():      # s --> (57656758,)
            list_appeared_id.append(s[0])

        for person in list_users_id:
            if person not in list_appeared_id:
                new_list_users_id.append(person)
    else:
        new_list_users_id = list_users_id
    return new_list_users_id       # уже обновленный возвращает, без старых ай ди


# функция для поиска из списка 3 самых популярных фото
def serch_popular(response):
    popular_list = []  # сюда будем заносить инфу о 3 самых популярных фото
    likes_list = []  # создадим список из лайков, ранжируем по убыванию, чтобы потом выбрать самые популярные фото
    for foto in response['items']:
        likes_list.append(foto['likes']['count'] + foto['comments']['count'])
    nessesary_likes = sorted(likes_list, reverse=True)  # отсортировали по убыванию, брать только первые 3 значения

    while len(popular_list) < 3:  # пока не отберем 3 популярные фотo, сравниваем каждое фото с максимальными лайками
        for foto in response['items']:
            if foto['likes']['count'] + foto['comments']['count'] == nessesary_likes[0] or foto['likes']['count'] + \
                    foto['comments']['count'] == nessesary_likes[1] or foto['likes']['count'] + foto['comments']['count'] == nessesary_likes[2]:
                popular_list.append(foto)
    return popular_list


# функция для поиска фото и формирования списка вложений
def get_fotos_info(list_users_id):
    info_fotos_for_upload = {}
    response = session_vk.method('photos.get', {
        'owner_id': list_users_id[0],
        'album_id': 'profile',
        'extended': 1})

    try:
        popular_list = serch_popular(response)

        info_ids_fotos = []  # в следующем цикле от каждой популярной фото берем id фото и пользователя
        for item in popular_list:
            info_ids_fotos.append(item['id'])
        info_fotos_for_upload[popular_list[0]['owner_id']] = info_ids_fotos

        # создаем формат для вложений из фото

        person = list_users_id[0]

        list_foto_attachments = []  # список вложений каждого отдельного пользователя формата ['photo7097751_266247043',..]
        for couple in info_fotos_for_upload[person]:
            list_foto_attachments.append(f'photo{person}_{couple}')

        list_attach = []
        foto_link = ','.join(list_foto_attachments)
        list_attach.append(foto_link)
        list_attach.append(person)

        del list_users_id[0]  # удаляем это ай ди чтобы при следующем сообщении пользователю отправлялся другой человек
        return list_attach

    except KeyError:
        return None


# функция для отправки текста сообщения
def write_msg(user_id, message, key=None):
    if key is not None:
        session.method('messages.send', {
            'user_id': user_id,
            'message': message,
            'random_id': randrange(10 ** 7),
            'keyboard': key.get_keyboard()
        })
    else:
        session.method('messages.send', {
            'user_id': user_id,
            'message': message,
            'random_id': randrange(10 ** 7)
        })


# функция для отправки фотографий
def send_foto(user_id, list_attach):
    session.method('messages.send', {
        'user_id': user_id,
        'message': f"https://vk.com/id{list_attach[1]}",
        'attachment': list_attach[0],
        'random_id': randrange(10 ** 7)})


for event in VkLongPoll(session).listen():
    if event.type == VkEventType.MESSAGE_NEW and event.to_me:
        txt = event.text.lower()
        user_id = event.user_id

        if txt == "привет":
            write_msg(user_id, f"Хай, {user_id}. Напиши 'старт', если хочешь подобрать себе пару", key=keyboard_start)
            user_info = get_user_info(user_id)
            missing_list = check_info(user_info)

        elif txt == "старт":
            if 'age' in missing_list:
                add_bdate(user_id)
            if 'city' in missing_list:
                city = add_city(user_id)
            if city is not None:
                list_users_id = serch_users(user_info)

                if list_users_id is not None:
                    if list_users_id == []:
                        write_msg(user_id, 'В вашем городе по вашим запросам ни не найдено')

                    else:
                        new_list_users_id = check_id(list_users_id)
                        if new_list_users_id == []:
                            write_msg(user_id, 'Вы уже просмотрели все варианты')
                        else:
                            write_msg(user_id,
                                      "Я подобрала несколько вариантов. Ответь 'дальше', если хочешь продолжить",
                                      key=keyboard_forward)

                            create_tables(engine)
                            new_list_users_id = check_id(list_users_id)

                else:
                    write_msg(user_id, "Ошибка, попробуйте позже")
            else:
                write_msg(user_id, "Ошибка, попробуйте позже")

        elif txt == "дальше":
            write_msg(user_id,
                      'отправляю фотографии. Ответь "дальше", если хочешь продолжить. Ответь "пока", если хочешь завершить',
                      key=keyboard_main)

            list_attach = get_fotos_info(new_list_users_id)
            if list_attach is not None:

                send_foto(user_id, list_attach)

                option1 = Options(user_id=user_id, option_id=list_attach[1], foto=list_attach[0], white_list='not defined')
                sessiondb.add_all([option1])
                sessiondb.commit()
            else:
                write_msg(user_id, "Ошибка в поиске фотографий, попробуйте позже")

        elif txt == "добавить в избранное":
            sessiondb.query(Options).filter(Options.option_id == list_attach[1] and Options.user_id == user_id).update({"white_list": "favourite"})
            sessiondb.commit()
            write_msg(user_id, "Добавлено в избранное. Ответь 'дальше', если хочешь продолжить", key=keyboard_forward)

        elif txt == "мое избранное":
            q = sessiondb.query(Options).filter(Options.white_list == 'favourite' and Options.user_id == user_id)
            message = "Твои избранные контакты:" + '\n'
            for s in q.all():
                message = message + f"https://vk.com/id{s.option_id}" + '\n'
            write_msg(user_id, message)
            write_msg(user_id, "Продолжаем? :)", key=keyboard_forward)

        elif txt == "пока":
            write_msg(user_id, "Удачи!")
