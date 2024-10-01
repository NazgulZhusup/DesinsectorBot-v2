import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
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

# Определение состояний
class Form(StatesGroup):
    name = State()
    object = State()
    insect_quantity = State()
    disinsect_experience = State()
    phone = State()
    address = State()

# Функция инициализации базы данных
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
    conn.commit()
    conn.close()

init_db()

async def start_bot(token):
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Обработчик команды /start
    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        await message.answer("Добрый день! Как к вам можно обращаться?")
        await state.set_state(Form.name)

    # Обработчик имени
    @dp.message(Form.name)
    async def process_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer(
            f"{message.text}, ответьте, пожалуйста, на несколько вопросов, чтобы мы могли просчитать стоимость дезинсекции.",
            reply_markup=kb.inl_kb_greetings
        )
        await state.set_state(Form.object)

    # Обработчик кнопки начала
    @dp.callback_query(F.data == 'start')
    async def process_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.answer(
            "Расскажите, пожалуйста, подробнее об объекте. У вас:",
            reply_markup=kb.inl_kb_object
        )
        await state.set_state(Form.insect_quantity)

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
        await state.set_state(Form.insect_quantity)

    # Обработчик количества насекомых
    @dp.callback_query(F.data.startswith('quantity_'))
    async def process_insect_quantity(callback: types.CallbackQuery, state: FSMContext):
        quantity_selected = callback.data.split('_')[1]
        await state.update_data(insect_quantity=quantity_selected)
        await callback.answer()
        await callback.message.answer(
            "Есть ли у вас опыт дезинсекции?",
            reply_markup=kb.inl_kb_experience
        )
        await state.set_state(Form.disinsect_experience)

    # Обработчик опыта дезинсекции
    @dp.callback_query(F.data.startswith('experience_'))
    async def process_disinsect_experience(callback: types.CallbackQuery, state: FSMContext):
        experience_selected = callback.data.split('_')[1]
        await state.update_data(disinsect_experience=experience_selected)
        await callback.answer()
        await callback.message.answer(
            "Пожалуйста, отправьте ваш номер телефона:",
            reply_markup=kb.kb_contact
        )
        await state.set_state(Form.phone)

    # Обработчик номера телефона (отправка контакта)
    @dp.message(Form.phone, F.content_type == types.ContentType.CONTACT)
    async def process_phone_contact(message: types.Message, state: FSMContext):
        if message.contact:
            phone = re.sub(r'\D', '', message.contact.phone_number)
            await state.update_data(phone=phone)
            await message.answer("Пожалуйста, введите ваш домашний адрес:")
            await state.set_state(Form.address)

    # Обработчик номера телефона (ввод вручную)
    @dp.message(Form.phone, F.content_type == types.ContentType.TEXT)
    async def process_phone_text(message: types.Message, state: FSMContext):
        phone = re.sub(r'\D', '', message.text)
        if not re.fullmatch(r'\d{10,15}', phone):
            await message.answer("Пожалуйста, введите корректный номер телефона, используя 10-15 цифр.")
            return
        await state.update_data(phone=phone)
        await message.answer("Пожалуйста, введите ваш домашний адрес:")
        await state.set_state(Form.address)

    # Обработчик домашнего адреса
    @dp.message(Form.address)
    async def process_address(message: types.Message, state: FSMContext):
        address = message.text.strip()
        if len(address) < 5:
            await message.answer("Пожалуйста, введите ваш домашний адрес.")
            return
        await state.update_data(address=address)

        user_data = await state.get_data()
        logging.info(f"Сохранение данных: {user_data}")

        # Сохранение данных в базу данных
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
            logging.info("Данные успешно сохранены в базу данных.")
        except Exception as e:
            logging.error(f"Ошибка при сохранении данных: {e}")
            await message.answer("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
            await state.clear()
            return

        await message.answer(f"Спасибо, {user_data.get('name')}! Ваши данные сохранены.\nТелефон: {user_data.get('phone')}\nАдрес: {user_data.get('address')}")
        await state.clear()

    async def main():
        try:
            await dp.start_polling(bot)
        finally:
            await bot.session.close()

    await main()

# Основная функция для запуска всех ботов
async def main():
    tasks = [start_bot(token) for token in TOKENS.values()]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
