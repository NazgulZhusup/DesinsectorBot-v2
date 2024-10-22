import sqlite3
import logging
import uuid
from disinsectors_bot import get_disinsector_token
from aiogram import Bot

def get_next_disinsector():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Получаем всех дезинсекторов
    cur.execute("SELECT id FROM disinsectors ORDER BY id ASC")
    disinsectors = cur.fetchall()

    if not disinsectors:
        print("Ошибка: нет доступных дезинсекторов.")
        conn.close()
        return None

    # Получаем количество заявок у каждого дезинсектора
    cur.execute("SELECT disinsector_id, COUNT(*) FROM orders WHERE disinsector_id IS NOT NULL GROUP BY disinsector_id")
    disinsector_counts = cur.fetchall()

    # Преобразуем результат в словарь: {disinsector_id: количество заявок}
    disinsector_dict = {row[0]: row[1] for row in disinsector_counts}

    # Ищем дезинсектора с наименьшим количеством заявок
    min_count = float('inf')
    selected_disinsector = None

    for disinsector in disinsectors:
        disinsector_id = disinsector[0]
        count = disinsector_dict.get(disinsector_id, 0)
        if count < min_count:
            min_count = count
            selected_disinsector = disinsector_id

    conn.close()

    if selected_disinsector is None:
        print("Ошибка: не удалось выбрать дезинсектора.")

    return selected_disinsector

def create_order(client_id, order_id, disinsector_id=None):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()

        # Логирование данных перед записью
        logging.info(f"Creating order for client_id={client_id}, disinsector_id={disinsector_id}, order_id={order_id}")

        cur.execute('''
            INSERT INTO orders (client_id, order_id, order_status, order_date, disinsector_id)
            VALUES (?, ?, 'Новая', date('now'), ?)
        ''', (client_id, order_id, disinsector_id))

        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Ошибка при создании заказа: {e}")

