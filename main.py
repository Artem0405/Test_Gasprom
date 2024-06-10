import datetime
import json
import os
import time
from typing import Dict, List

from flask import Flask, request, jsonify

app = Flask(__name__)

# Файл базы данных (может быть заменен на базу данных)
DB_FILE = 'birthday_db.json'

# Загружаем данные из файла базы данных
try:
    with open(DB_FILE, 'r') as f:
        birthday_db = json.load(f)
except FileNotFoundError:
    birthday_db = {}


# --- Модуль авторизации ---
def authenticate_user(username, password):
    """Проверяет учетные данные пользователя."""
    # В реальном приложении следует использовать более надежную авторизацию
    if username in birthday_db:
        if birthday_db[username]['password'] == password:
            return True
    return False


# --- Модуль подключения к базе данных ---
def get_user_data(username):
    """Получает данные пользователя из базы данных."""
    if username in birthday_db:
        return birthday_db[username]
    return None


def update_user_data(username, data):
    """Обновляет данные пользователя в базе данных."""
    birthday_db[username] = data
    save_database()


def save_database():
    """Сохраняет данные в файл."""
    with open(DB_FILE, 'w') as f:
        json.dump(birthday_db, f)


# --- Модуль подписки ---
def subscribe_to_birthday(username, target_username):
    """Подписывает пользователя на уведомления о дне рождения другого пользователя."""
    user_data = get_user_data(username)
    if user_data is None:
        return False

    if 'subscriptions' not in user_data:
        user_data['subscriptions'] = []
    if target_username not in user_data['subscriptions']:
        user_data['subscriptions'].append(target_username)
        update_user_data(username, user_data)
        return True
    return False


def unsubscribe_from_birthday(username, target_username):
    """Отписывает пользователя от уведомлений о дне рождения другого пользователя."""
    user_data = get_user_data(username)
    if user_data is None:
        return False

    if 'subscriptions' in user_data and target_username in user_data['subscriptions']:
        user_data['subscriptions'].remove(target_username)
        update_user_data(username, user_data)
        return True
    return False


# --- Модуль оповещения (cron) ---
def send_birthday_notifications():
    """Отправляет уведомления о днях рождения."""
    today = datetime.date.today()
    for username, user_data in birthday_db.items():
        if 'birthday' in user_data:
            birthday_date = datetime.date(today.year, user_data['birthday']['month'], user_data['birthday']['day'])
            if birthday_date == today:
                # Отправляем уведомление всем подписанным на этот день рождения
                for subscriber in user_data.get('subscriptions', []):
                    # Реализация отправки уведомлений
                    print(f"Отправляем поздравление {subscriber} с днем рождения {username}")


def send_birthday_reminder(username, user_data):
    """Отправляет напоминание о дне рождения пользователя за определенное количество дней."""
    # Получение данных о дне рождения пользователя
    birthday_month = user_data['birthday']['month']
    birthday_day = user_data['birthday']['day']

    # Определение количества дней до дня рождения
    reminder_days = int(user_data.get('reminder_days', 1))

    # Получение даты дня рождения
    birthday_date = datetime.date(datetime.date.today().year, birthday_month, birthday_day)

    # Проверка, нужно ли отправить напоминание
    if (birthday_date - datetime.date.today()).days == reminder_days:
        # Отправка напоминания
        print(f"Отправляем напоминание о дне рождения {username} за {reminder_days} дней")


# --- API ---
@app.route('/login', methods=['POST'])
def login():
    """Авторизация пользователя."""
    username = request.json.get('username')
    password = request.json.get('password')
    if authenticate_user(username, password):
        return jsonify({'message': 'Авторизация прошла успешно'})
    return jsonify({'error': 'Неверный логин или пароль'}), 401


@app.route('/register', methods=['POST'])
def register():
    """Регистрация пользователя."""
    username = request.json.get('username')
    password = request.json.get('password')
    birthday = request.json.get('birthday')
    if username in birthday_db:
        return jsonify({'error': 'Пользователь с таким именем уже существует'}), 400
    if birthday is None:
        return jsonify({'error': 'Не указана дата рождения'}), 400

    birthday_data = {
        'month': int(birthday['month']),
        'day': int(birthday['day'])
    }

    new_user = {
        'password': password,
        'birthday': birthday_data
    }
    birthday_db[username] = new_user
    save_database()
    return jsonify({'message': 'Пользователь успешно зарегистрирован'}), 201


@app.route('/users', methods=['GET'])
def get_users():
    """Получение списка пользователей."""
    return jsonify(birthday_db)


@app.route('/subscribe/<username>/<target_username>', methods=['POST'])
def subscribe(username, target_username):
    """Подписка на уведомления о дне рождения."""
    if subscribe_to_birthday(username, target_username):
        return jsonify({'message': 'Вы успешно подписались на уведомления'})
    return jsonify({'error': 'Ошибка подписки'}), 400


@app.route('/unsubscribe/<username>/<target_username>', methods=['POST'])
def unsubscribe(username, target_username):
    """Отписка от уведомлений о дне рождения."""
    if unsubscribe_from_birthday(username, target_username):
        return jsonify({'message': 'Вы успешно отписались от уведомлений'})
    return jsonify({'error': 'Ошибка отписки'}), 400


@app.route('/profile/<username>', methods=['GET'])
def get_profile(username):
    """Получение профиля пользователя."""
    user_data = get_user_data(username)
    if user_data is None:
        return jsonify({'error': 'Пользователь не найден'}), 404
    return jsonify(user_data)


@app.route('/profile/<username>', methods=['PUT'])
def update_profile(username):
    """Обновление профиля пользователя."""
    user_data = get_user_data(username)
    if user_data is None:
        return jsonify({'error': 'Пользователь не найден'}), 404

    updated_data = request.json
    for key, value in updated_data.items():
        user_data[key] = value

    update_user_data(username, user_data)
    return jsonify({'message': 'Профиль успешно обновлен'}), 200


# Запуск приложения
if __name__ == '__main__':
    # Запуск cron-подобного процесса для отправки напоминаний
    while True:
        send_birthday_notifications()
        for username, user_data in birthday_db.items():
            send_birthday_reminder(username, user_data)
        time.sleep(60)  # Проверка каждые 60 секунд
    app.run(debug=True)