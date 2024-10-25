import sqlite3
from aiogram import Bot, types
import logging

def get_disinsector_token(disinsector_id):
    try:
        conn = sqlite3.connect('disinsect_data.db')
        cur = conn.cursor()
        cur.execute("SELECT token FROM disinsectors WHERE id = ?", (disinsector_id,))
        result = cur.fetchone()
        return result[0] if result else None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении токена дезинсектора: {e}")
        return None
    finally:
        if conn:
            conn.close()

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

# shared_functions.py

async def send_notification_to_disinsector_and_start_questions(disinsector_id, order_id):
    token = get_disinsector_token(disinsector_id)
    if token:
        bot = Bot(token=token)
        try:
            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()

            # Получаем user_id дезинсектора
            cur.execute("SELECT user_id FROM disinsectors WHERE id = ?", (disinsector_id,))
            result = cur.fetchone()
            if result:
                disinsector_user_id = result[0]
                if disinsector_user_id:

                    # Получаем данные заказа
                    cur.execute('''
                        SELECT o.order_id, c.name, c.address, o.object_type, o.insect_quantity
                        FROM orders o
                        JOIN clients c ON o.client_id = c.id
                        WHERE o.order_id = ?
                    ''', (order_id,))
                    order_data = cur.fetchone()

                    if order_data:
                        message_text = (
                            f"Новая заявка от {order_data[1]}.\n"
                            f"Объект: {order_data[3]}\n"
                            f"Адрес: {order_data[2]}\n"
                            f"Количество насекомых: {order_data[4]}\n"
                            "Согласны взять заявку в работу?"
                        )
                        inline_kb = types.InlineKeyboardMarkup(
                            inline_keyboard=[
                                [
                                    types.InlineKeyboardButton(
                                        text="OK",
                                        callback_data=f"accept_order_{order_id}"
                                    ),
                                    types.InlineKeyboardButton(
                                        text="Нет",
                                        callback_data=f"decline_order_{order_id}"
                                    )
                                ]
                            ]
                        )
                        await bot.send_message(chat_id=disinsector_user_id, text=message_text, reply_markup=inline_kb)
                    else:
                        logging.error(f"Не удалось получить данные заказа с order_id {order_id}")
                else:
                    logging.error(f"User ID дезинсектора {disinsector_id} не найден.")
            else:
                logging.error(f"Дезинсектор с ID {disinsector_id} не найден.")
        except Exception as e:
            logging.error(f"Ошибка при отправке уведомления дезинсектору: {e}")
        finally:
            await bot.session.close()
            if conn:
                conn.close()
    else:
        logging.error(f"Токен не найден для дезинсектора с ID {disinsector_id}")


