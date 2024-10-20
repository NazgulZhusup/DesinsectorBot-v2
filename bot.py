import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import logging
import re
import uuid
import keyboards as kb
from config import TOKEN


client_token = TOKEN
bot = Bot(token=client_token)  # Создаем объект бота
storage = MemoryStorage()  # Инициализируем хранилище для FSM
dp = Dispatcher(bot=bot, storage=storage)  # Передаем объект бота в диспетчер


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)

# Определение состояний для клиентов
class ClientForm(StatesGroup):
    name = State()
    object = State()
    insect_quantity = State()
    disinsect_experience = State()
    phone = State()
    address = State()


# Функция для получения дезинсектора по токену
def get_disinsector_by_token(token):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('SELECT id, name FROM disinsectors WHERE token = ?', (token,))
    disinsector = cur.fetchone()
    conn.close()
    return disinsector

# Функция инициализации базы данных (общая)
def init_db():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            object TEXT NOT NULL,
            insect_quantity TEXT NOT NULL,
            disinsect_experience TEXT NOT NULL,
            phone TEXT NOT NULL,
            address TEXT NOT NULL
        )
        ''')

    # Создание таблицы orders
    cur.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_id INTEGER NOT NULL, 
                disinsector_id INTEGER, 
                order_id TEXT NOT NULL,
                order_status TEXT DEFAULT 'Новая',
                order_date TEXT,
                estimated_price INTEGER,
                final_price INTEGER,
                poison_type TEXT,
                insect_type TEXT,
                insect_quantity TEXT,
                client_contact TEXT,
                client_address TEXT,
                client_property_type TEXT,
                client_area INTEGER,
                FOREIGN KEY (client_id) REFERENCES users(id)  -- Внешний ключ
            )
            ''')

    # Создание таблицы clients
    cur.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            ''')

    # Создание таблицы admins
    cur.execute('''
            CREATE TABLE IF NOT EXISTS admins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            ''')

    # Создание таблицы disinsectors
    cur.execute('''
            CREATE TABLE IF NOT EXISTS disinsectors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                token TEXT NOT NULL UNIQUE
            )
            ''')
    conn.commit()
    conn.close()

init_db()

# Функция для получения дезинсектора по стратегии Round-Robin
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

# Функция для создания новой заявки (синхронная)
def create_order_sync(user_data, disinsector_id, state):
    # Проверка наличия всех необходимых данных в user_data
    required_keys = ['name', 'object', 'insect_quantity', 'disinsect_experience', 'phone', 'address']
    for key in required_keys:
        if key not in user_data:
            print(f"Ошибка: отсутствует {key} в user_data")
            return

    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    disinsector_id = get_next_disinsector()  # Получаем дезинсектора по стратегии
    order_id = str(uuid.uuid4())[:8]  # Уникальный идентификатор заявки, обрезанный до 8 символов

    # Вставляем данные в таблицу users
    cur.execute('''
        INSERT INTO users (name, object, insect_quantity, disinsect_experience, phone, address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        user_data['name'],
        user_data['object'],
        user_data['insect_quantity'],
        user_data['disinsect_experience'],
        user_data['phone'],
        user_data['address']
    ))

    user_id = cur.lastrowid  # Получаем ID пользователя из последнего вставленного ряда

    order_id = user_data.get('order_id', f"ORD{user_id}")

    # Вставляем данные в таблицу orders
    cur.execute('''
            INSERT INTO orders (client_id, order_id, order_status, order_date, estimated_price, final_price, poison_type, insect_type, insect_quantity, client_contact, client_address, client_property_type, client_area, disinsector_id)
            VALUES (?, ?, ?, date('now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
        user_id,  # client_id ссылается на ID из таблицы users
        order_id,
        'Новая',  # Статус заявки по умолчанию
        1000,  # Пример сметной стоимости
        1200,  # Пример окончательной стоимости
        user_data.get('poison_type', None),  # Тип химиката
        user_data.get('insect_type', None),  # Вид насекомого
        user_data.get('insect_quantity', None),  # Количество насекомых
        user_data.get('phone', None),  # Телефон клиента
        user_data.get('address', None),  # Адрес клиента
        user_data.get('property_type', None),  # Тип помещения
        user_data.get('area', None),  # Площадь помещения
        disinsector_id  # Назначенный дезинсектор
    ))

    conn.commit()
    conn.close()


# Асинхронная обёртка для создания заявки
async def create_order(user_data, disinsector_id, state):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, create_order_sync, user_data, disinsector_id, state)
    await send_notification_to_disinsector_and_start_questions(disinsector_id, user_data, state)


# Запуск бота для клиентов
async def start_client_bot(token):
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        await message.answer("Добрый день! Как к вам можно обращаться?")
        await state.set_state(ClientForm.name)

    # Обработчик имени
    @dp.message(ClientForm.name)
    async def process_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer(
            f"{message.text}, ответьте, пожалуйста, на несколько вопросов, чтобы мы могли просчитать стоимость дезинсекции.",
            reply_markup=kb.inl_kb_greetings  # Клавиатура с кнопкой "Начать"
        )
        await state.set_state(ClientForm.object)

    # Обработчик кнопки "Начать"
    @dp.callback_query(F.data == 'start')
    async def process_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.answer(
            "Расскажите, пожалуйста, подробнее об объекте. У вас:",
            reply_markup=kb.inl_kb_object  # Клавиатура для выбора объекта
        )
        await state.set_state(ClientForm.object)

    # Обработчик выбора объекта
    @dp.callback_query(F.data.startswith('object_'))
    async def process_object(callback: types.CallbackQuery, state: FSMContext):
        object_selected = callback.data.split('_')[1]
        await state.update_data(object=object_selected)
        await callback.answer()
        await callback.message.answer(
            "Сколько насекомых вы обнаружили?",
            reply_markup=kb.inl_kb_insect_quantity  # Клавиатура для выбора количества насекомых
        )
        await state.set_state(ClientForm.insect_quantity)

    # Обработчик количества насекомых
    @dp.callback_query(F.data.startswith('quantity_'))
    async def process_insect_quantity(callback: types.CallbackQuery, state: FSMContext):
        quantity_selected = callback.data.split('_')[1]
        await state.update_data(insect_quantity=quantity_selected)
        await callback.answer()
        await callback.message.answer(
            "Есть ли у вас опыт дезинсекции?",
            reply_markup=kb.inl_kb_experience  # Клавиатура для выбора опыта дезинсекции
        )
        await state.set_state(ClientForm.disinsect_experience)

    # Обработчик опыта дезинсекции
    @dp.callback_query(F.data.startswith('experience_'))
    async def process_disinsect_experience(callback: types.CallbackQuery, state: FSMContext):
        experience_selected = callback.data.split('_')[1]
        await state.update_data(disinsect_experience=experience_selected)
        await callback.answer()
        await callback.message.answer(
            "Пожалуйста, отправьте ваш номер телефона:",
            reply_markup=kb.kb_contact  # Кнопка для отправки контакта
        )
        await state.set_state(ClientForm.phone)

    # Обработчик номера телефона (отправка контакта)
    @dp.message(ClientForm.phone, F.content_type == types.ContentType.CONTACT)
    async def process_phone_contact(message: types.Message, state: FSMContext):
        phone = re.sub(r'\D', '', message.contact.phone_number)
        await state.update_data(phone=phone)
        await message.answer("Пожалуйста, введите ваш домашний адрес:")
        await state.set_state(ClientForm.address)

    # Обработчик номера телефона (ввод вручную)
    @dp.message(ClientForm.phone, F.content_type == types.ContentType.TEXT)
    async def process_phone_text(message: types.Message, state: FSMContext):
        phone = re.sub(r'\D', '', message.text)
        if not re.fullmatch(r'\d{10,15}', phone):
            await message.answer("Пожалуйста, введите корректный номер телефона, используя 10-15 цифр.")
            return
        await state.update_data(phone=phone)
        await message.answer("Пожалуйста, введите ваш домашний адрес:")
        await state.set_state(ClientForm.address)

    # Обработчик домашнего адреса
    @dp.message(ClientForm.address)
    async def process_address(message: types.Message, state: FSMContext):
        address = message.text.strip()
        if len(address) < 5:
            await message.answer("Пожалуйста, введите ваш домашний адрес.")
            return
        await state.update_data(address=address)

        user_data = await state.get_data()

        # Получаем ID дезинсектора
        disinsector_id = get_next_disinsector()

        # Проверяем, удалось ли назначить дезинсектора
        if disinsector_id is None:
            await message.answer("Ошибка: не удалось назначить дезинсектора. Попробуйте позже.")
            return

        await create_order(user_data, disinsector_id, state)

        await message.answer(
            f"Спасибо, {user_data.get('name')}! Ваши данные сохранены.\nТелефон: {user_data.get('phone')}\nАдрес: {user_data.get('address')}")
        await state.clear()

    await dp.start_polling(bot)


class DisinsectorForm(StatesGroup):
    poison_type = State()
    insect_type = State()
    client_area = State()
    estimated_price = State()

async def start_disinsector_bot(token):
    logging.info(f"Starting disinsector bot with token: {token}")
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Стартовая команда
    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        disinsector = get_disinsector_by_token(token)
        if disinsector:
            user_id = message.from_user.id  # Получаем Telegram user_id
            await message.answer(f"Добро пожаловать, {disinsector[1]}! Ваш user_id: {user_id}")

            await state.update_data(disinsector_id=disinsector[0])

            # Отправляем вопрос с кнопками
            logging.info(f"Disinsector {disinsector[1]} ({disinsector[0]}) logged in")
            await message.answer("Какой химикат будет использоваться?")
            await message.answer("Выберите химикат:", reply_markup=kb.inl_kb_poison_type)
            await state.set_state(DisinsectorForm.poison_type)
        else:
            await message.answer("Ошибка авторизации.")



    # Обработчик выбора химиката
    @dp.callback_query(F.data.startswith('poison_'))
    async def process_poison_selection(callback: types.CallbackQuery, state: FSMContext):
        print(f"Received callback with data: {callback.data}")  # Для отладки
        poison_type = callback.data.split('_')[1]
        await state.update_data(poison_type=poison_type)
        await callback.answer()  # Закрыть уведомление на кнопке

        # Задаем следующий вопрос с кнопками
        await callback.message.answer("Какой вид насекомого?", reply_markup=kb.inl_kb_insect_type)
        await state.set_state(DisinsectorForm.insect_type)


    # Обработчик выбора насекомого
    @dp.callback_query(F.data.startswith('insect_'))
    async def process_insect_selection(callback: types.CallbackQuery, state: FSMContext):
        insect_type = callback.data.split('_')[1]
        await state.update_data(insect_type=insect_type)
        await callback.answer()  # Закрыть уведомление на кнопке

        # Задаем следующий вопрос для ввода площади помещения
        await callback.message.answer("Какова площадь помещения? Введите числовое значение.")
        await state.set_state(DisinsectorForm.client_area)

    # Обработчик ввода площади помещения
    @dp.message(DisinsectorForm.client_area)
    async def process_client_area(message: types.Message, state: FSMContext):
        try:
            client_area = float(message.text)
            await state.update_data(client_area=client_area)
            logging.info(f"Client area successfully parsed: {client_area}")

            # Задаем следующий вопрос
            await message.answer("Какова предварительная стоимость? Введите числовое значение.")
            await state.set_state(DisinsectorForm.estimated_price)
        except ValueError:
            logging.error(f"Failed to parse client area: {message.text}")
            await message.answer("Пожалуйста, введите числовое значение.")

    # Обработчик ввода предварительной стоимости
    @dp.message(DisinsectorForm.estimated_price)
    async def process_estimated_price(message: types.Message, state: FSMContext):
        try:
            estimated_price = float(message.text)
            await state.update_data(estimated_price=estimated_price)

            # Сохраняем данные
            user_data = await state.get_data()
            order_id = user_data['order_id']
            poison_type = user_data['poison_type']
            insect_type = user_data['insect_type']
            client_area = user_data['client_area']
            estimated_price = user_data['estimated_price']

            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()
            cur.execute('''
                UPDATE orders 
                SET poison_type = ?, insect_type = ?, client_area = ?, estimated_price = ?
                WHERE order_id = ?
            ''', (poison_type, insect_type, client_area, estimated_price, order_id))
            conn.commit()
            conn.close()

            await message.answer(f"Данные заявки {order_id} обновлены:\n"
                                 f"Химикат: {poison_type}\n"
                                 f"Вид насекомого: {insect_type}\n"
                                 f"Площадь помещения: {client_area} кв.м\n"
                                 f"Предварительная стоимость: {estimated_price} рублей")
            await state.clear()

        except ValueError:
            await message.answer("Пожалуйста, введите числовое значение для стоимости.")

    # Запуск диспетчера
    await dp.start_polling(bot)

def update_order_by_disinsector(order_id, poison_type, insect_type, estimated_price, final_price, order_status):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    cur.execute('''
        UPDATE orders 
        SET poison_type = ?, insect_type = ?, estimated_price = ?, final_price = ?, order_status = ?
        WHERE order_id = ?
    ''', (
        poison_type,
        insect_type,
        estimated_price,
        final_price,
        order_status,
        order_id
    ))

    conn.commit()
    conn.close()


# Основная функция для запуска всех ботов
async def main():
    # Запуск клиента
    client_token = TOKEN
    tasks = [start_client_bot(client_token)]

    # Получаем все токены дезинсекторов и запускаем их ботов
    disinsector_tokens = get_all_disinsector_tokens()
    for token in disinsector_tokens:
        tasks.append(start_disinsector_bot(token))

    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())