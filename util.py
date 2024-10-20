import sqlite3
import logging
from aiogram import Bot
from disinsectors_bot import DisinsectorForm
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
        count = disinsector_dict.get(disinsector_id, 0)  # Если у дезинсектора нет заявок, возвращаем 0
        if count < min_count:
            min_count = count
            selected_disinsector = disinsector_id

    conn.close()

    if selected_disinsector is None:
        print("Ошибка: не удалось выбрать дезинсектора.")

    return selected_disinsector


def get_disinsector_token(disinsector_id):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute("SELECT token FROM disinsectors WHERE id = ?", (disinsector_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None

def get_disinsector_user_id(disinsector_id):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM disinsectors WHERE id = ?", (disinsector_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else None



def get_all_disinsector_tokens():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute("SELECT token FROM disinsectors")
    tokens = [row[0] for row in cur.fetchall()]
    conn.close()

    logging.info(f"Loaded disinsector tokens: {tokens}")
    return tokens


# Функция для отправки уведомления дезинсектору о новой заявке
async def send_notification_to_disinsector_and_start_questions(disinsector_id, user_data, state):
    # Получаем токен дезинсектора
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
                message_text = f"Новая заявка: {user_data['name']}, объект: {user_data['object']}. Какой химикат будет использоваться?"
                await bot.send_message(chat_id=disinsector_user_id, text=message_text)
                await state.set_state(DisinsectorForm.poison_type)
            else:
                print(f"Ошибка: не удалось найти user_id для дезинсектора с ID {disinsector_id}")
    else:
        print(f"Ошибка: Токен не найден для дезинсектора с ID {disinsector_id}")
