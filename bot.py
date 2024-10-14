import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import sqlite3
import logging
import re
import keyboards as kb
from config import TOKENS

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("bot.log"),
        logging.StreamHandler()
    ]
)


# Определение состояний для клиентов и дезинсекторов
class ClientForm(StatesGroup):
    name = State()
    object = State()
    insect_quantity = State()
    disinsect_experience = State()
    phone = State()
    address = State()


class DisinsectorForm(StatesGroup):
    token = State()  # Ввод токена дезинсектора
    name = State()  # Имя дезинсектора после авторизации по токену


# Функция инициализации базы данных
def init_db():
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Создание таблицы для клиентов
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

    # Создание таблицы для дезинсекторов
    cur.execute('''
    CREATE TABLE IF NOT EXISTS disinsectors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        token TEXT NOT NULL UNIQUE,
        phone TEXT
    )
    ''')

    conn.commit()
    conn.close()


init_db()


# Функция для показа данных дезинсектора
async def show_disinsector_data(message: types.Message, disinsector):
    conn = sqlite3.connect('disinsect_data.db')
    cur = conn.cursor()

    # Выводим приветствие и информацию о дезинсекторе
    await message.answer(f"Здравствуйте, {disinsector[1]}! Вот информация о ваших клиентах:")

    # Получение количества клиентов и заявок
    cur.execute("SELECT COUNT(*) FROM users")
    client_count = cur.fetchone()[0]

    await message.answer(f"У вас {client_count} клиентов. Вы можете получить список клиентов и информацию по заявкам.")

    # Получение и отправка списка клиентов
    cur.execute("SELECT name, phone, address FROM users")
    clients = cur.fetchall()

    if clients:
        clients_info = "\n".join([f"{client[0]}, Телефон: {client[1]}, Адрес: {client[2]}" for client in clients])
        await message.answer(f"Список клиентов:\n{clients_info}")
    else:
        await message.answer("На данный момент у вас нет клиентов.")

    conn.close()


async def start_bot(token):
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Обработчик команды /start для клиентов
    @dp.message(commands=["start"])
    async def start_client_command(message: types.Message, state: FSMContext):
        await message.answer("Добро пожаловать! Как к вам можно обращаться?")
        await state.set_state(ClientForm.name)

    # Обработчик ввода имени клиента
    @dp.message(ClientForm.name)
    async def process_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer(
            f"{message.text}, ответьте, пожалуйста, на несколько вопросов, чтобы мы могли просчитать стоимость дезинсекции.",
            reply_markup=kb.inl_kb_greetings
        )
        await state.set_state(ClientForm.object)

    # Обработчик кнопки начала
    @dp.callback_query(F.data == 'start')
    async def process_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.answer(
            "Расскажите, пожалуйста, подробнее об объекте. У вас:",
            reply_markup=kb.inl_kb_object
        )
        await state.set_state(ClientForm.insect_quantity)

    # Обработчик выбора объекта
    @dp.callback_query(F.data.startswith('object_'))
    async def process_object(callback: types.CallbackQuery, state: FSMContext):
        object_selected = callback.data.split('_')[1]
        await state.update_data(object=object_selected)
        await callback.answer()
        await callback.message.answer(
            "Сколько насекомых вы обнаружили?",
            reply_markup=kb.inl_kb_insect_quantity
        )
        await state.set_state(ClientForm.insect_quantity)

    # Обработчик выбора количества насекомых
    @dp.callback_query(F.data.startswith('quantity_'))
    async def process_insect_quantity(callback: types.CallbackQuery, state: FSMContext):
        quantity_selected = callback.data.split('_')[1]
        await state.update_data(insect_quantity=quantity_selected)
        await callback.answer()
        await callback.message.answer(
            "Есть ли у вас опыт дезинсекции?",
            reply_markup=kb.inl_kb_experience
        )
        await state.set_state(ClientForm.disinsect_experience)

    # Обработчик выбора опыта дезинсекции
    @dp.callback_query(F.data.startswith('experience_'))
    async def process_disinsect_experience(callback: types.CallbackQuery, state: FSMContext):
        experience_selected = callback.data.split('_')[1]
        await state.update_data(disinsect_experience=experience_selected)
        await callback.answer()
        await callback.message.answer(
            "Пожалуйста, отправьте ваш номер телефона:",
            reply_markup=kb.kb_contact
        )
        await state.set_state(ClientForm.phone)

    # Обработчик номера телефона
    @dp.message(ClientForm.phone, F.content_type == types.ContentType.CONTACT)
    async def process_phone_contact(message: types.Message, state: FSMContext):
        if message.contact:
            phone = re.sub(r'\D', '', message.contact.phone_number)
            await state.update_data(phone=phone)
            await message.answer("Пожалуйста, введите ваш домашний адрес:")
            await state.set_state(ClientForm.address)

    # Обработчик ввода телефона вручную
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
        logging.info(f"Сохранение данных: {user_data}")

        # Сохранение данных клиента в базу данных
        try:
            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()
            cur.execute('''
            INSERT INTO users (name, object, insect_quantity, disinsect_experience, phone, address)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                user_data.get('name'),
                user_data.get('object'),
                user_data.get('insect_quantity'),
                user_data.get('disinsect_experience'),
                user_data.get('phone'),
                user_data.get('address')
            ))
            conn.commit()
            conn.close()
            logging.info("Данные клиента успешно сохранены в базу данных.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении данных: {e}")
            await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
            await state.clear()
            return

        await message.answer(f"Спасибо, {user_data.get('name')}! Ваши данные сохранены.")
        await state.clear()

        # Обработчик команды /login для дезинсекторов
        @dp.message(commands="login")
        async def login_command(message: types.Message, state: FSMContext):
            await message.answer("Пожалуйста, введите ваш персональный токен для авторизации:")
            await state.set_state(DisinsectorForm.token)

        # Обработчик ввода токена дезинсектора
        @dp.message(DisinsectorForm.token)
        async def process_token(message: types.Message, state: FSMContext):
            token_input = message.text.strip()

            # Проверяем наличие токена в базе данных
            conn = sqlite3.connect('disinsect_data.db')
            cur = conn.cursor()
            cur.execute("SELECT * FROM disinsectors WHERE token = ?", (token_input,))
            disinsector = cur.fetchone()
            conn.close()

            if disinsector:
                await message.answer(f"Добро пожаловать, {disinsector[1]}! Вы успешно авторизованы.")
                await state.clear()
                # Показать меню или данные дезинсектора
                await show_disinsector_data(message, disinsector)
            else:
                await message.answer("Токен неверен, попробуйте снова.")
                await state.clear()

        async def main():
            try:
                await dp.start_polling(bot)
            finally:
                await bot.session.close()

    # Основная функция для запуска всех ботов
    async def main():
        tasks = [start_bot(bot_token) for bot_token in TOKENS.values()]
        await asyncio.gather(*tasks)

    if __name__ == '__main__':
        asyncio.run(main())


