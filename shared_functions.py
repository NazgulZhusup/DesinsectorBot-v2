import sqlite3
from aiogram import Bot, types
import logging

def get_disinsector_token(disinsector_id):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute("SELECT token FROM disinsectors WHERE id = ?", (disinsector_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

async def send_notification_to_disinsector(disinsector_id, message_text):
    token = get_disinsector_token(disinsector_id)
    if token:
        async with Bot(token=token) as bot:
            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()
            cur.execute("SELECT user_id FROM disinsectors WHERE id = ?", (disinsector_id,))
            result = cur.fetchone()
            conn.close()

            if result:
                disinsector_user_id = result[0]

                if disinsector_user_id is None or not isinstance(disinsector_user_id, (int, str)):
                    print(f"Ошибка: некорректный chat_id для дезинсектора с ID {disinsector_id}")
                    return

                await bot.send_message(chat_id=disinsector_user_id, text=message_text)
            else:
                print(f"Ошибка: не удалось найти user_id для дезинсектора с ID {disinsector_id}")
    else:
        print(f"Ошибка: Токен не найден для дезинсектора с ID {disinsector_id}")


def get_next_disinsector():
    try:
        with sqlite3.connect('disinsect_data.db') as conn:
            cur = conn.cursor()

            # Получаем всех дезинсекторов
            cur.execute("SELECT id FROM disinsectors ORDER BY id ASC")
            disinsectors = cur.fetchall()

            if not disinsectors:
                logging.error("Ошибка: нет доступных дезинсекторов.")
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

            if selected_disinsector is None:
                logging.error("Ошибка: не удалось выбрать дезинсектора.")
            else:
                logging.info(f"Выбран дезинсектор с ID: {selected_disinsector} с {min_count} заявками")

            return selected_disinsector
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении следующего дезинсектора: {e}")
        return None


