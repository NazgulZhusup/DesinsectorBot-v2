import asyncio
import logging
import re
import uuid

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

import keyboards as kb
from config import TOKEN
from db import add_order
from shared_functions import get_next_disinsector
from disinsectors_bot import send_notification_to_disinsector_and_start_questions
from shared_functions import send_notification_to_disinsector

client_token = TOKEN
bot = Bot(token=client_token)
storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage)

class ClientForm(StatesGroup):
    name = State()
    object = State()
    insect_quantity = State()
    disinsect_experience = State()
    phone = State()
    address = State()

async def start_client_bot(token):
    bot = Bot(token=token)
    storage = MemoryStorage()
    dp = Dispatcher(bot=bot, storage=storage)

    @dp.message(CommandStart())
    async def start_command(message: types.Message, state: FSMContext):
        await message.answer("Добрый день! Как к вам можно обращаться?")
        await state.set_state(ClientForm.name)

    @dp.message(ClientForm.name)
    async def process_name(message: types.Message, state: FSMContext):
        await state.update_data(name=message.text)
        await message.answer(
            f"{message.text}, ответьте, пожалуйста, на несколько вопросов, чтобы мы могли просчитать стоимость дезинсекции.",
            reply_markup=kb.inl_kb_greetings
        )
        await state.set_state(ClientForm.object)

    @dp.callback_query(F.data == 'start')
    async def process_start(callback: types.CallbackQuery, state: FSMContext):
        await callback.answer()
        await callback.message.answer(
            "Расскажите, пожалуйста, подробнее об объекте. У вас:",
            reply_markup=kb.inl_kb_object
        )
        await state.set_state(ClientForm.object)

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

    @dp.message(ClientForm.phone, F.content_type == types.ContentType.CONTACT)
    async def process_phone_contact(message: types.Message, state: FSMContext):
        phone = re.sub(r'\D', '', message.contact.phone_number)
        await state.update_data(phone=phone)
        await message.answer("Пожалуйста, введите ваш домашний адрес:")
        await state.set_state(ClientForm.address)

    @dp.message(ClientForm.phone, F.content_type == types.ContentType.TEXT)
    async def process_phone_text(message: types.Message, state: FSMContext):
        phone = re.sub(r'\D', '', message.text)
        if not re.fullmatch(r'\d{10,15}', phone):
            await message.answer("Пожалуйста, введите корректный номер телефона.")
            return
        await state.update_data(phone=phone)
        await message.answer("Пожалуйста, введите ваш домашний адрес:")
        await state.set_state(ClientForm.address)

    @dp.message(ClientForm.address)
    async def process_address(message: types.Message, state: FSMContext):
        address = message.text.strip()
        if len(address) < 5:
            await message.answer("Пожалуйста, введите ваш домашний адрес.")
            return
        await state.update_data(address=address)

        # Получаем все данные из состояния
        user_data = await state.get_data()

        # Генерируем или используем существующий order_id
        order_id = user_data.get('order_id')
        if not order_id:
            order_id = str(uuid.uuid4())[:8]  # Генерация уникального идентификатора заявки
            await state.update_data(order_id=order_id)
            logging.info(f"Новый order_id сгенерирован: {order_id}")
        else:
            logging.info(f"Существующий order_id: {order_id}")

        # Проверяем обновленные данные состояния
        user_data = await state.get_data()

        # Назначение дезинсектора
        disinsector_id = get_next_disinsector()

        if disinsector_id is None:
            await message.answer("Ошибка: не удалось назначить дезинсектора. Попробуйте позже.")
            return

        # Сохраняем заказ в базу данных
        add_order(
            order_id=order_id,
            disinsector_id=disinsector_id,
            name=user_data['name'],
            object_type=user_data['object'],
            insect_quantity=user_data['insect_quantity'],
            disinsect_experience=user_data['disinsect_experience'],
            phone=user_data['phone'],
            address=user_data['address'],
            status='Новая'
        )

        # Отправка уведомления дезинсектору
        message_text = f"Новая заявка от {user_data['name']}. Объект: {user_data['object']}, Адрес: {user_data['address']}, Количество насекомых: {user_data['insect_quantity']}"
        await send_notification_to_disinsector(disinsector_id, message_text)
        await send_notification_to_disinsector_and_start_questions(disinsector_id, user_data, state)

        await message.answer(
            f"Спасибо, {user_data['name']}! Ваши данные сохранены.\n"
            f"Телефон: {user_data['phone']}\nАдрес: {user_data['address']}"
        )

        # Очищаем состояние
        await state.clear()

    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(start_client_bot(TOKEN))

