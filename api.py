from flask import Flask, request, jsonify
import sqlite3
from apscheduler.schedulers.background import BackgroundScheduler
import requests
import logging

app = Flask(__name__)


# Функция для инициализации базы данных
def init_db():
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()

    # Создание таблицы пользователей, если она не существует
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL UNIQUE,
        user_phone TEXT NOT NULL,
        user_name TEXT NOT NULL,
        user_lastname TEXT NOT NULL,
        user_order_quantity INTEGER NOT NULL DEFAULT 0,
        user_discount REAL
    )
    ''')

    # Создание таблицы заказов, если она не существует
    cur.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_phone TEXT NOT NULL,
        user_name TEXT NOT NULL,
        user_lastname TEXT NOT NULL,
        order_id TEXT NOT NULL,
        order_amount REAL NOT NULL
    )
    ''')

    conn.commit()
    conn.close()


# Инициализация базы данных
init_db()


# Функция для сохранения заказа в базу данных
def save_order(order_data):
    try:
        conn = sqlite3.connect('orders.db', timeout=5)
        conn.execute('PRAGMA journal_mode=WAL;')
        cur = conn.cursor()
        cur.execute('''
        INSERT INTO orders (user_phone, user_name, user_lastname, order_id, order_amount)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            order_data['Userphone'],
            order_data['Username'],
            order_data['UserLastname'],
            order_data['OrderID'],
            order_data['OrderAmount']
        ))
        conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при сохранении заказа: {e}")
    finally:
        conn.close()


# Функция для отправки обновления скидки на вебхук
def send_discount_update(user_id, user_discount):
    webhook_url = "YOUR_WEBHOOK_URL"  # Замените на ваш вебхук
    payload = {
        "userId": user_id,
        "userDiscount": user_discount
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 200:
            logging.info("Данные успешно отправлены на вебхук.")
        else:
            logging.error(f"Ошибка при отправке данных на вебхук: {response.status_code} {response.text}")
    except Exception as e:
        logging.error(f"Ошибка при соединении с вебхуком: {e}")


# Процедура для обновления скидок
def update_user_discounts():
    conn = sqlite3.connect('orders.db')
    cur = conn.cursor()

    # Получаем пользователей, у которых количество заказов >= 3 и поле user_discount пустое
    cur.execute('''
    SELECT user_id FROM users 
    WHERE user_order_quantity >= 3 AND user_discount IS NULL
    ''')

    user_ids = cur.fetchall()

    for (user_id,) in user_ids:
        # Обновляем поле user_discount для таких пользователей
        cur.execute('''
        UPDATE users 
        SET user_discount = 3 
        WHERE user_id = ?
        ''', (user_id,))

        # Отправляем данные на вебхук
        send_discount_update(user_id, 3)  # Отправляем user_discount равным 3

    conn.commit()
    conn.close()


# Запуск планировщика
scheduler = BackgroundScheduler()
scheduler.add_job(update_user_discounts, 'interval', days=1)  # Запускаем раз в сутки
scheduler.start()


# API-эндпоинт для создания заказа
@app.route('/api/orders', methods=['POST'])
def receive_order():
    try:
        order_data = request.json  # Получаем данные в формате JSON
        save_order(order_data)  # Сохраняем заказ в базе данных

        # Проверяем, существует ли пользователь в таблице users
        user_id = order_data.get("UserID")
        user_phone = order_data.get("Userphone")
        user_name = order_data.get("Username")
        user_lastname = order_data.get("UserLastname")

        # Добавляем или обновляем пользователя
        conn = sqlite3.connect('orders.db')
        cur = conn.cursor()

        # Проверяем, существует ли пользователь
        cur.execute('''
        SELECT * FROM users WHERE user_id = ?
        ''', (user_id,))
        user = cur.fetchone()

        if user:
            # Увеличиваем количество заказов
            cur.execute('''
            UPDATE users
            SET user_order_quantity = user_order_quantity + 1
            WHERE user_id = ?
            ''', (user_id,))
        else:
            # Добавляем нового пользователя
            cur.execute('''
            INSERT INTO users (user_id, user_phone, user_name, user_lastname)
            VALUES (?, ?, ?, ?)
            ''', (user_id, user_phone, user_name, user_lastname))

        conn.commit()
        conn.close()

        return jsonify({"status": "success", "message": "Order saved successfully."}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == '__main__':
    app.run(port=5000)  # Запуск API на порту 5000
